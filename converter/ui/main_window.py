"""
Main Application Window for OmniConvert.
Integrates the modern dark glassmorphic interface, dynamic file queue, batch converter, and hardware monitor.
"""

import os
import uuid
import subprocess
from typing import List, Dict, Optional
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFileDialog, QMessageBox, QFrame
)
from PyQt6.QtGui import QIcon, QFont

from converter.ui.styles import MODERN_STYLE_SHEET
from converter.ui.widgets import DropZoneWidget, FileQueueItemWidget, TelemetryDockWidget, PowerProfileWidget
from converter.core.worker import ConversionQueueManager, QueueItem
from converter.engines.base import ConversionProgress


class MainWindow(QMainWindow):
    """OmniConvert main application window."""

    def __init__(self, initial_files: Optional[List[str]] = None):
        super().__init__()
        self.setWindowTitle("OmniConvert — Universal High-Fidelity File Converter")
        self.resize(960, 720)
        self.setMinimumSize(820, 560)

        self.queue_manager = ConversionQueueManager()
        self.item_widgets: Dict[str, FileQueueItemWidget] = {}
        self.custom_output_dir: Optional[str] = None

        self._setup_ui()
        self._connect_signals()

        if initial_files:
            self.add_files(initial_files)

    def _setup_ui(self):
        self.setStyleSheet(MODERN_STYLE_SHEET)

        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(20, 16, 20, 16)
        root_layout.setSpacing(14)

        # 1. Header Bar
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        lbl_title = QLabel("🔮 OmniConvert", self)
        lbl_title.setObjectName("headerTitle")
        lbl_subtitle = QLabel("Universal Lossless & High-Fidelity File Converter • Low Hardware Footprint", self)
        lbl_subtitle.setObjectName("headerSubtitle")
        title_vbox.addWidget(lbl_title)
        title_vbox.addWidget(lbl_subtitle)
        header_layout.addLayout(title_vbox)

        header_layout.addStretch(1)

        # Power Profile Selector
        lbl_profile = QLabel("Power Mode:", self)
        lbl_profile.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        header_layout.addWidget(lbl_profile)

        self.power_widget = PowerProfileWidget(self)
        self.power_widget.mode_changed.connect(self._on_power_mode_changed)
        header_layout.addWidget(self.power_widget)

        root_layout.addLayout(header_layout)

        # 2. Drag & Drop Zone
        self.drop_zone = DropZoneWidget(self)
        self.drop_zone.files_dropped.connect(self.add_files)
        root_layout.addWidget(self.drop_zone)

        # 3. Queue Action Toolbar
        toolbar_frame = QFrame(self)
        toolbar_frame.setStyleSheet("background: transparent;")
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(0, 4, 0, 4)
        toolbar_layout.setSpacing(10)

        self.lbl_queue_count = QLabel("Queue (0 files)", self)
        self.lbl_queue_count.setObjectName("sectionTitle")
        toolbar_layout.addWidget(self.lbl_queue_count)

        toolbar_layout.addStretch(1)

        # Output folder button
        self.btn_output_dir = QPushButton("📁 Output: Same as Input", self)
        self.btn_output_dir.setProperty("class", "btnSecondary")
        self.btn_output_dir.setToolTip("Click to select a custom output folder")
        self.btn_output_dir.clicked.connect(self._choose_output_directory)
        toolbar_layout.addWidget(self.btn_output_dir)

        # Clear Completed Button
        self.btn_clear = QPushButton("Clear Finished", self)
        self.btn_clear.setProperty("class", "btnSecondary")
        self.btn_clear.clicked.connect(self._clear_completed_items)
        toolbar_layout.addWidget(self.btn_clear)

        # Batch Convert All Button
        self.btn_convert_all = QPushButton("⚡ Convert All", self)
        self.btn_convert_all.setProperty("class", "btnPrimary")
        self.btn_convert_all.clicked.connect(self._convert_all)
        toolbar_layout.addWidget(self.btn_convert_all)

        root_layout.addWidget(toolbar_frame)

        # 4. Scrollable Queue Container
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: transparent; border: none;")

        self.queue_container = QWidget()
        self.queue_container.setStyleSheet("background-color: transparent;")
        self.queue_layout = QVBoxLayout(self.queue_container)
        self.queue_layout.setContentsMargins(0, 0, 0, 0)
        self.queue_layout.setSpacing(8)
        self.queue_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Empty queue placeholder
        self.lbl_empty = QLabel("No files in queue. Drag & drop files above or click to browse.", self.queue_container)
        self.lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty.setStyleSheet("color: #475569; font-size: 13px; padding: 40px 0;")
        self.queue_layout.addWidget(self.lbl_empty)

        self.scroll_area.setWidget(self.queue_container)
        root_layout.addWidget(self.scroll_area, 1)

        # 5. Bottom Hardware Telemetry Dock
        self.telemetry_dock = TelemetryDockWidget(self)
        root_layout.addWidget(self.telemetry_dock)

    def _connect_signals(self):
        self.queue_manager.signals.started.connect(self._on_item_started)
        self.queue_manager.signals.progress.connect(self._on_item_progress)
        self.queue_manager.signals.completed.connect(self._on_item_completed)
        self.queue_manager.signals.failed.connect(self._on_item_failed)
        self.queue_manager.queue_finished.connect(self._on_queue_finished)

    def _on_power_mode_changed(self, mode: str):
        self.queue_manager.set_power_mode(mode)

    def _choose_output_directory(self):
        chosen = QFileDialog.getExistingDirectory(self, "Select Output Directory", "")
        if chosen:
            self.custom_output_dir = chosen
            folder_name = os.path.basename(chosen) or chosen
            self.btn_output_dir.setText(f"📁 Output: {folder_name}")
            self.btn_output_dir.setToolTip(f"Output folder: {chosen}")

    def add_files(self, file_paths: List[str]):
        """Add batch of files to conversion queue."""
        added_count = 0
        for path in file_paths:
            if not os.path.isfile(path):
                continue
            item_id = str(uuid.uuid4())
            item_widget = FileQueueItemWidget(item_id, path, self.queue_container)

            item_widget.convert_requested.connect(self._convert_single)
            item_widget.remove_requested.connect(self._remove_item)
            item_widget.target_changed.connect(self._on_target_changed)

            self.item_widgets[item_id] = item_widget
            self.queue_layout.addWidget(item_widget)

            # Register with QueueManager
            target_dir = self.custom_output_dir or os.path.dirname(path)
            queue_item = QueueItem(
                item_id=item_id,
                source_path=path,
                target_format=item_widget.get_selected_target(),
                target_dir=target_dir,
                options={"lossless": True, "power_mode": self.power_widget.current_mode}
            )
            self.queue_manager.add_item(queue_item)
            added_count += 1

        if added_count > 0:
            self.lbl_empty.setVisible(False)
            self._update_queue_count()

    def _on_target_changed(self, item_id: str, new_target: str):
        if item_id in self.queue_manager.items:
            self.queue_manager.items[item_id].target_format = new_target

    def _remove_item(self, item_id: str):
        if item_id in self.item_widgets:
            widget = self.item_widgets.pop(item_id)
            self.queue_layout.removeWidget(widget)
            widget.deleteLater()
            self.queue_manager.remove_item(item_id)
            self._update_queue_count()
            if not self.item_widgets:
                self.lbl_empty.setVisible(True)

    def _clear_completed_items(self):
        to_remove = []
        for item_id, item in self.queue_manager.items.items():
            if item.status in ("completed", "cancelled"):
                to_remove.append(item_id)
        for item_id in to_remove:
            self._remove_item(item_id)

    def _update_queue_count(self):
        count = len(self.item_widgets)
        self.lbl_queue_count.setText(f"Queue ({count} {'file' if count == 1 else 'files'})")

    def _convert_single(self, item_id: str):
        if item_id in self.item_widgets:
            self.item_widgets[item_id].set_converting()
            # Update target directory if custom chosen
            if self.custom_output_dir:
                self.queue_manager.items[item_id].target_dir = self.custom_output_dir
            self.queue_manager.start_conversion(item_id)

    def _convert_all(self):
        if not self.item_widgets:
            return
        for item_id, widget in self.item_widgets.items():
            item = self.queue_manager.items.get(item_id)
            if item and item.status in ("queued", "failed", "cancelled"):
                widget.set_converting()
                if self.custom_output_dir:
                    item.target_dir = self.custom_output_dir
        self.queue_manager.start_all()

    @pyqtSlot(str)
    def _on_item_started(self, item_id: str):
        if item_id in self.item_widgets:
            self.item_widgets[item_id].set_converting()

    @pyqtSlot(str, object)
    def _on_item_progress(self, item_id: str, prog: ConversionProgress):
        if item_id in self.item_widgets:
            self.item_widgets[item_id].update_progress(prog)

    @pyqtSlot(str, str)
    def _on_item_completed(self, item_id: str, target_path: str):
        if item_id in self.item_widgets:
            self.item_widgets[item_id].set_completed(target_path)

    @pyqtSlot(str, str)
    def _on_item_failed(self, item_id: str, error_msg: str):
        if item_id in self.item_widgets:
            self.item_widgets[item_id].set_failed(error_msg)

    @pyqtSlot()
    def _on_queue_finished(self):
        pass
