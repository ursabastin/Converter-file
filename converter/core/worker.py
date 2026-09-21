"""
Asynchronous Worker and Task Queue Manager for OmniConvert.
Runs conversion jobs in background threads with low hardware priority, adaptive power profiles, and Qt signals.
"""

import os
import sys
import psutil
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool

from converter.engines.base import ConversionProgress, CancellationToken
from converter.core.registry import registry


class WorkerSignals(QObject):
    started = pyqtSignal(str)  # item_id
    progress = pyqtSignal(str, object)  # item_id, ConversionProgress
    completed = pyqtSignal(str, str)  # item_id, target_path
    failed = pyqtSignal(str, str)  # item_id, error_message


@dataclass
class QueueItem:
    item_id: str
    source_path: str
    target_format: str
    target_dir: str
    options: Dict[str, Any] = field(default_factory=dict)
    cancel_token: CancellationToken = field(default_factory=CancellationToken)
    status: str = "queued"  # queued, converting, completed, failed, cancelled
    target_path: Optional[str] = None
    error_message: Optional[str] = None


class ConversionTask(QRunnable):
    """QRunnable task executing a single file conversion."""

    def __init__(self, item: QueueItem, signals: WorkerSignals, power_mode: str = "balanced"):
        super().__init__()
        self.item = item
        self.signals = signals
        self.power_mode = power_mode

    def run(self):
        if self.item.cancel_token.is_cancelled:
            self.item.status = "cancelled"
            return

        self.item.status = "converting"
        self.signals.started.emit(self.item.item_id)

        try:
            src_ext = registry.get_extension(self.item.source_path)
            dst_ext = self.item.target_format.lower().lstrip(".")

            base_name = os.path.splitext(os.path.basename(self.item.source_path))[0]
            target_filename = f"{base_name}.{dst_ext}"
            target_path = os.path.join(self.item.target_dir, target_filename)

            # Avoid accidental overwrite if file exists with same name by appending counter
            counter = 1
            final_target_path = target_path
            while os.path.exists(final_target_path) and os.path.abspath(final_target_path) != os.path.abspath(self.item.source_path):
                final_target_path = os.path.join(self.item.target_dir, f"{base_name}_{counter}.{dst_ext}")
                counter += 1

            self.item.target_path = final_target_path

            engine = registry.resolve_engine(src_ext, dst_ext)
            if not engine:
                raise ValueError(f"No conversion engine found for {src_ext} -> {dst_ext}")

            # Merge options with power mode
            opts = dict(self.item.options)
            opts["power_mode"] = self.power_mode

            def progress_callback(prog: ConversionProgress):
                self.signals.progress.emit(self.item.item_id, prog)

            success = engine.convert(
                source_path=self.item.source_path,
                target_path=final_target_path,
                options=opts,
                progress_callback=progress_callback,
                cancel_token=self.item.cancel_token
            )

            if success:
                self.item.status = "completed"
                self.signals.completed.emit(self.item.item_id, final_target_path)
            else:
                raise RuntimeError("Conversion returned false.")

        except Exception as e:
            if self.item.cancel_token.is_cancelled:
                self.item.status = "cancelled"
                self.signals.failed.emit(self.item.item_id, "Conversion cancelled by user.")
            else:
                self.item.status = "failed"
                self.item.error_message = str(e)
                self.signals.failed.emit(self.item.item_id, str(e))


class ConversionQueueManager(QObject):
    """Manages thread pool, power profiles, and job dispatch."""

    queue_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()
        self.thread_pool = QThreadPool()
        self.power_mode = "balanced"
        self._apply_power_mode("balanced")
        self.items: Dict[str, QueueItem] = {}
        self.active_count = 0

        self.signals.completed.connect(self._on_item_done)
        self.signals.failed.connect(self._on_item_done)

    def set_power_mode(self, mode: str):
        """Switch power mode: 'eco', 'balanced', or 'turbo'."""
        self.power_mode = mode.lower()
        self._apply_power_mode(self.power_mode)

    def _apply_power_mode(self, mode: str):
        p = psutil.Process(os.getpid())
        if sys.platform == "win32":
            try:
                if mode == "eco":
                    p.nice(psutil.IDLE_PRIORITY_CLASS)
                    self.thread_pool.setMaxThreadCount(1)
                elif mode == "balanced":
                    p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                    self.thread_pool.setMaxThreadCount(2)
                elif mode == "turbo":
                    p.nice(psutil.NORMAL_PRIORITY_CLASS)
                    cores = os.cpu_count() or 4
                    self.thread_pool.setMaxThreadCount(max(2, cores // 2))
            except Exception:
                pass
        else:
            if mode == "eco":
                self.thread_pool.setMaxThreadCount(1)
            elif mode == "balanced":
                self.thread_pool.setMaxThreadCount(2)
            else:
                self.thread_pool.setMaxThreadCount(4)

    def add_item(self, item: QueueItem):
        self.items[item.item_id] = item

    def remove_item(self, item_id: str):
        if item_id in self.items:
            self.items[item_id].cancel_token.cancel()
            del self.items[item_id]

    def clear(self):
        for item in self.items.values():
            item.cancel_token.cancel()
        self.items.clear()

    def start_conversion(self, item_id: str):
        if item_id in self.items:
            item = self.items[item_id]
            if item.status in ("queued", "failed", "cancelled"):
                self.active_count += 1
                task = ConversionTask(item, self.signals, self.power_mode)
                self.thread_pool.start(task)

    def start_all(self):
        for item in self.items.values():
            if item.status in ("queued", "failed", "cancelled"):
                self.active_count += 1
                task = ConversionTask(item, self.signals, self.power_mode)
                self.thread_pool.start(task)

    def cancel_all(self):
        for item in self.items.values():
            item.cancel_token.cancel()

    def _on_item_done(self, item_id: str, _param: str):
        self.active_count = max(0, self.active_count - 1)
        if self.active_count == 0:
            self.queue_finished.emit()
