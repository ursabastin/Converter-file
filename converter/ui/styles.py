"""
Modern Dark Glassmorphic Design System & QSS Stylesheet for OmniConvert.
Features sleek translucent cards, glowing accents, polished controls, and buttery smooth aesthetics.
"""

MODERN_STYLE_SHEET = """
/* Global Window Styling */
QMainWindow, QWidget#centralWidget {
    background-color: #0B0E14;
    color: #F3F4F6;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', 'Inter', -apple-system, sans-serif;
    font-size: 13px;
}

/* ScrollBars */
QScrollBar:vertical {
    border: none;
    background: #0F121A;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #2D3548;
    min-height: 25px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #6366F1;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Glassmorphic Container Cards */
QFrame.glassCard {
    background-color: #141824;
    border: 1px solid #232A3B;
    border-radius: 12px;
}

QFrame.glassCardHighlight {
    background-color: #181D2C;
    border: 1px solid #363E56;
    border-radius: 12px;
}

/* Labels */
QLabel {
    color: #E2E8F0;
}
QLabel#headerTitle {
    font-size: 20px;
    font-weight: 700;
    color: #FFFFFF;
    letter-spacing: -0.5px;
}
QLabel#headerSubtitle {
    font-size: 12px;
    color: #94A3B8;
}
QLabel#sectionTitle {
    font-size: 14px;
    font-weight: 600;
    color: #CBD5E1;
}

/* Primary Action Buttons */
QPushButton.btnPrimary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:1 #4F46E5);
    color: #FFFFFF;
    font-weight: 600;
    font-size: 13px;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
}
QPushButton.btnPrimary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #818CF8, stop:1 #6366F1);
}
QPushButton.btnPrimary:pressed {
    background: #4338CA;
}
QPushButton.btnPrimary:disabled {
    background: #232736;
    color: #64748B;
}

/* Secondary Buttons */
QPushButton.btnSecondary {
    background-color: #1E2333;
    color: #E2E8F0;
    font-weight: 500;
    font-size: 12px;
    border: 1px solid #2F374E;
    border-radius: 8px;
    padding: 8px 16px;
}
QPushButton.btnSecondary:hover {
    background-color: #272E42;
    border-color: #4F5A7D;
    color: #FFFFFF;
}
QPushButton.btnSecondary:pressed {
    background-color: #171B27;
}

/* Danger / Cancel Buttons */
QPushButton.btnDanger {
    background-color: rgba(239, 68, 68, 0.12);
    color: #FCA5A5;
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 11px;
}
QPushButton.btnDanger:hover {
    background-color: rgba(239, 68, 68, 0.25);
    border-color: #EF4444;
    color: #FFFFFF;
}

/* Mini Buttons (Row actions) */
QPushButton.btnMini {
    background-color: #1E2333;
    color: #94A3B8;
    border: 1px solid #2B3245;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
}
QPushButton.btnMini:hover {
    background-color: #2A3248;
    color: #FFFFFF;
    border-color: #6366F1;
}

/* Combo Boxes */
QComboBox {
    background-color: #191E2C;
    color: #F8FAFC;
    border: 1px solid #2D364D;
    border-radius: 6px;
    padding: 6px 12px;
    min-width: 90px;
    font-size: 12px;
    font-weight: 500;
}
QComboBox:hover {
    border-color: #6366F1;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #141824;
    color: #F1F5F9;
    selection-background-color: #6366F1;
    selection-color: #FFFFFF;
    border: 1px solid #2D364D;
    border-radius: 6px;
    outline: none;
    padding: 4px;
}

/* Progress Bars */
QProgressBar {
    background-color: #161A26;
    border: 1px solid #242B3C;
    border-radius: 5px;
    height: 8px;
    text-align: center;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #06B6D4, stop:1 #6366F1);
    border-radius: 4px;
}

/* Badges */
QLabel.badgeCategory {
    background-color: #1E2333;
    color: #818CF8;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    border: 1px solid #313A53;
}
QLabel.badgeSuccess {
    background-color: rgba(16, 185, 129, 0.15);
    color: #34D399;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    border: 1px solid rgba(16, 185, 129, 0.3);
}
QLabel.badgeConverting {
    background-color: rgba(245, 158, 11, 0.15);
    color: #FBBF24;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    border: 1px solid rgba(245, 158, 11, 0.3);
}
QLabel.badgeFailed {
    background-color: rgba(239, 68, 68, 0.15);
    color: #F87171;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    border: 1px solid rgba(239, 68, 68, 0.3);
}

/* Tooltips */
QToolTip {
    background-color: #191E2C;
    color: #F8FAFC;
    border: 1px solid #363E56;
    padding: 6px;
    border-radius: 6px;
    font-size: 11px;
}
"""
