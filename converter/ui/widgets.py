"""
Modern PyQt6 Custom UI Widgets for OmniConvert.
Includes DropZoneWidget, FileQueueItemWidget, TelemetryDockWidget, and PowerProfileWidget.
"""

import os
import subprocess
from typing import List, Optional
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QProgressBar, QComboBox, QFrame, QFileDialog, QSizePolicy
)
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QColor, QPainter, QPen

from converter.engines.base import ConversionProgress
from converter.core.registry import registry
from converter.core.telemetry import format_bytes, format_duration, HardwareMonitor, EmaEtaCalculator


class DropZoneWidget(QFrame):
    """Interactive drag and drop zone with dashed border animation and file dialog click."""

    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.is_hovered = False
        self.setMinimumHeight(130)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)

        icon_label = QLabel("📥", self)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 32px; background: transparent;")

        title_label = QLabel("Drag & Drop any files here", self)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #F1F5F9; background: transparent;")

        subtitle_label = QLabel("or click to browse files • Supports Images, Video, Audio, Docs, Data, Archives & Code", self)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("font-size: 11px; color: #94A3B8; background: transparent;")

        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        bg_color = QColor("#181D2C") if self.is_hovered else QColor("#131622")
        painter.setBrush(bg_color)

        # Border
        pen_color = QColor("#6366F1") if self.is_hovered else QColor("#2A3247")
        pen = QPen(pen_color, 1.8, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 12, 12)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            self.is_hovered = True
            self.update()
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.is_hovered = False
        self.update()

    def dropEvent(self, event: QDropEvent):
        self.is_hovered = False
        self.update()
        paths = []
        for url in event.mimeData().urls():
            local_path = url.toLocalFile()
            if local_path and os.path.exists(local_path):
                paths.append(local_path)
        if paths:
            self.files_dropped.emit(paths)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "Select Files to Convert",
                "",
                "All Files (*.*)"
            )
            if files:
                self.files_dropped.emit(files)


class FileQueueItemWidget(QFrame):
    """Card widget representing a queued file with real-time ETA, speed, and conversion options."""

    convert_requested = pyqtSignal(str)  # item_id
    remove_requested = pyqtSignal(str)   # item_id
    target_changed = pyqtSignal(str, str) # item_id, target_format

    def __init__(self, item_id: str, file_path: str, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.file_path = file_path
        self.output_path: Optional[str] = None
        self.eta_calculator = EmaEtaCalculator()

        self.setObjectName("fileQueueCard")
        self.setProperty("class", "glassCard")
        self.setStyleSheet("""
            QFrame#fileQueueCard {
                background-color: #141824;
                border: 1px solid #232A3B;
                border-radius: 10px;
                padding: 4px;
            }
            QFrame#fileQueueCard:hover {
                border-color: #343E57;
            }
        """)

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # Top row: File details & target format selector
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # Category icon/badge
        category = registry.detect_category(self.file_path)
        category_icons = {
            "Image": "🖼️",
            "Video": "🎬",
            "Audio": "🎵",
            "Document": "📄",
            "Spreadsheet/Data": "📊",
            "Archive": "📦",
            "Code/Data": "💾",
            "Universal/Binary": "🧩"
        }
        self.category_badge = QLabel(f"{category_icons.get(category, '📄')} {category.upper()}", self)
        self.category_badge.setProperty("class", "badgeCategory")
        top_row.addWidget(self.category_badge)

        # Filename & size
        file_name = os.path.basename(self.file_path)
        file_size = os.path.getsize(self.file_path) if os.path.exists(self.file_path) else 0

        self.name_label = QLabel(file_name, self)
        self.name_label.setStyleSheet("font-weight: 600; color: #FFFFFF; font-size: 13px;")
        self.name_label.setToolTip(self.file_path)
        top_row.addWidget(self.name_label, 1)

        size_label = QLabel(format_bytes(file_size), self)
        size_label.setStyleSheet("color: #64748B; font-size: 11px;")
        top_row.addWidget(size_label)

        # Target Format Selector
        arrow_label = QLabel("➔", self)
        arrow_label.setStyleSheet("color: #6366F1; font-weight: bold; font-size: 14px;")
        top_row.addWidget(arrow_label)

        self.target_combo = QComboBox(self)
        targets = registry.get_compatible_targets(self.file_path)
        for t in targets:
            self.target_combo.addItem(t.upper(), t)
        self.target_combo.currentIndexChanged.connect(self._on_target_changed)
        top_row.addWidget(self.target_combo)

        # Status badge
        self.status_badge = QLabel("Queued", self)
        self.status_badge.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        top_row.addWidget(self.status_badge)

        # Single convert button
        self.btn_convert = QPushButton("Convert", self)
        self.btn_convert.setProperty("class", "btnMini")
        self.btn_convert.clicked.connect(lambda: self.convert_requested.emit(self.item_id))
        top_row.addWidget(self.btn_convert)

        # Open folder button (hidden until completed)
        self.btn_open = QPushButton("Open", self)
        self.btn_open.setProperty("class", "btnMini")
        self.btn_open.setVisible(False)
        self.btn_open.clicked.connect(self._open_output_folder)
        top_row.addWidget(self.btn_open)

        # Remove button
        self.btn_remove = QPushButton("✕", self)
        self.btn_remove.setProperty("class", "btnDanger")
        self.btn_remove.setToolTip("Remove from queue")
        self.btn_remove.clicked.connect(lambda: self.remove_requested.emit(self.item_id))
        top_row.addWidget(self.btn_remove)

        main_layout.addLayout(top_row)

        # Bottom row: Progress bar + Telemetry metrics (ETA & Speed)
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        bottom_row.addWidget(self.progress_bar, 1)

        self.telemetry_label = QLabel("Ready", self)
        self.telemetry_label.setStyleSheet("color: #64748B; font-size: 11px; min-width: 170px;")
        self.telemetry_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        bottom_row.addWidget(self.telemetry_label)

        main_layout.addLayout(bottom_row)

    def _on_target_changed(self):
        target_fmt = self.target_combo.currentData()
        if target_fmt:
            self.target_changed.emit(self.item_id, target_fmt)

    def get_selected_target(self) -> str:
        return self.target_combo.currentData() or "webp"

    def set_converting(self):
        self.status_badge.setText("Converting...")
        self.status_badge.setStyleSheet("color: #FBBF24; font-size: 11px; font-weight: 600;")
        self.btn_convert.setEnabled(False)
        self.target_combo.setEnabled(False)

    def update_progress(self, prog: ConversionProgress):
        self.progress_bar.setValue(int(prog.progress))

        # Speed and ETA readout
        speed_str = f"{format_bytes(prog.speed_bytes_sec)}/s" if prog.speed_bytes_sec > 0 else ""
        eta_str = f"ETA: {format_duration(prog.eta_seconds)}" if prog.eta_seconds > 0 else ""
        fps_str = f"{prog.fps:.0f} fps" if prog.fps > 0 else ""

        parts = [p for p in [fps_str, speed_str, eta_str] if p]
        self.telemetry_label.setText(" • ".join(parts) if parts else prog.status_text or f"{int(prog.progress)}%")

    def set_completed(self, output_path: str):
        self.output_path = output_path
        self.progress_bar.setValue(100)
        self.status_badge.setText("Completed ✓")
        self.status_badge.setStyleSheet("color: #34D399; font-size: 11px; font-weight: 600;")
        self.telemetry_label.setText("Finished 100%")
        self.btn_convert.setVisible(False)
        self.btn_open.setVisible(True)

    def set_failed(self, error_msg: str):
        self.status_badge.setText("Failed ✕")
        self.status_badge.setStyleSheet("color: #F87171; font-size: 11px; font-weight: 600;")
        self.telemetry_label.setText(error_msg[:40] + "..." if len(error_msg) > 40 else error_msg)
        self.telemetry_label.setToolTip(error_msg)
        self.btn_convert.setEnabled(True)
        self.target_combo.setEnabled(True)

    def _open_output_folder(self):
        if self.output_path and os.path.exists(self.output_path):
            if os.name == "nt":
                subprocess.Popen(f'explorer /select,"{os.path.abspath(self.output_path)}"')
            else:
                subprocess.Popen(["xdg-open", os.path.dirname(self.output_path)])


class TelemetryDockWidget(QFrame):
    """Bottom telemetry dock displaying real-time CPU %, RAM, and conversion throughput."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.monitor = HardwareMonitor()
        self.setProperty("class", "glassCardHighlight")
        self.setStyleSheet("""
            QFrame {
                background-color: #10141F;
                border: 1px solid #1F2637;
                border-radius: 8px;
                padding: 6px 14px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(24)

        # CPU Metric
        cpu_box = QHBoxLayout()
        cpu_box.setSpacing(6)
        lbl_cpu_icon = QLabel("⚡ CPU:", self)
        lbl_cpu_icon.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        self.lbl_cpu_val = QLabel("0%", self)
        self.lbl_cpu_val.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: 700;")
        cpu_box.addWidget(lbl_cpu_icon)
        cpu_box.addWidget(self.lbl_cpu_val)
        layout.addLayout(cpu_box)

        # RAM Metric
        ram_box = QHBoxLayout()
        ram_box.setSpacing(6)
        lbl_ram_icon = QLabel("🧠 Memory:", self)
        lbl_ram_icon.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        self.lbl_ram_val = QLabel("0 MB", self)
        self.lbl_ram_val.setStyleSheet("color: #A78BFA; font-size: 11px; font-weight: 700;")
        ram_box.addWidget(lbl_ram_icon)
        ram_box.addWidget(self.lbl_ram_val)
        layout.addLayout(ram_box)

        # Priority & Safety Indicator
        safety_box = QHBoxLayout()
        safety_box.setSpacing(6)
        lbl_safe_icon = QLabel("🛡️ Safety:", self)
        lbl_safe_icon.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        self.lbl_safe_val = QLabel("Below Normal Priority (Zero Stutter)", self)
        self.lbl_safe_val.setStyleSheet("color: #34D399; font-size: 11px; font-weight: 500;")
        safety_box.addWidget(lbl_safe_icon)
        safety_box.addWidget(self.lbl_safe_val)
        layout.addLayout(safety_box)

        layout.addStretch(1)

        # Global command active status
        term_label = QLabel("🚀 CLI: anyotherterminal -converter active", self)
        term_label.setStyleSheet("color: #64748B; font-size: 11px;")
        layout.addWidget(term_label)

        # Start non-intrusive 1.5-second timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_telemetry)
        self.timer.start(1500)

    def _refresh_telemetry(self):
        stats = self.monitor.snapshot()
        self.lbl_cpu_val.setText(f"{stats['system_cpu_pct']:.0f}% (App: {stats['process_cpu_pct']:.0f}%)")
        self.lbl_ram_val.setText(f"{stats['process_ram_mb']:.0f} MB ({stats['system_ram_pct']:.0f}% Sys)")


class PowerProfileWidget(QFrame):
    """Segmented toggle for Eco, Balanced, and Turbo power modes."""

    mode_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_mode = "balanced"
        self.setStyleSheet("""
            QFrame {
                background-color: #141824;
                border: 1px solid #232A3B;
                border-radius: 8px;
                padding: 2px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        self.btn_eco = QPushButton("🌿 Eco", self)
        self.btn_balanced = QPushButton("⚖️ Balanced", self)
        self.btn_turbo = QPushButton("⚡ Turbo", self)

        for btn in [self.btn_eco, self.btn_balanced, self.btn_turbo]:
            btn.setCheckable(True)
            btn.setFixedHeight(26)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #94A3B8;
                    border: none;
                    border-radius: 6px;
                    padding: 0 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    color: #F1F5F9;
                    background: #1B2132;
                }
                QPushButton:checked {
                    background: #6366F1;
                    color: #FFFFFF;
                }
            """)

        self.btn_eco.clicked.connect(lambda: self._set_mode("eco"))
        self.btn_balanced.clicked.connect(lambda: self._set_mode("balanced"))
        self.btn_turbo.clicked.connect(lambda: self._set_mode("turbo"))

        self.btn_balanced.setChecked(True)

        layout.addWidget(self.btn_eco)
        layout.addWidget(self.btn_balanced)
        layout.addWidget(self.btn_turbo)

    def _set_mode(self, mode: str):
        self.current_mode = mode
        self.btn_eco.setChecked(mode == "eco")
        self.btn_balanced.setChecked(mode == "balanced")
        self.btn_turbo.setChecked(mode == "turbo")
        self.mode_changed.emit(mode)
