"""Centralized terminal-style theme for the Kraken Bot shell and dashboard."""
from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import QEvent, QObject, QPropertyAnimation, QTimer, Qt
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QFrame,
                               QGraphicsDropShadowEffect, QGroupBox, QHeaderView,
                               QLineEdit, QPushButton, QTableView, QWidget)

from dashboard.styles import (ACCENT_COLOR, BACKGROUND_COLOR, BORDER_COLOR, CARD_COLOR,
                              ERROR_COLOR, INFO_COLOR, PANEL_COLOR, PRIMARY_COLOR, SECONDARY_TEXT,
                              TEXT_COLOR, WARNING_COLOR, table_style)


def application_style():
    return f"""
    QMainWindow, QWidget {{ background:{BACKGROUND_COLOR}; color:{TEXT_COLOR}; font-family:'Segoe UI'; font-size:11px; }}
    QLabel[role="pageTitle"] {{ color:{TEXT_COLOR}; font-size:18px; font-weight:700; background:transparent; border:0; }}
    QLabel[role="subtitle"] {{ color:{SECONDARY_TEXT}; font-size:10px; background:transparent; border:0; }}
    QLabel[role="information"] {{ background:#0C1B26; color:{SECONDARY_TEXT}; border:1px solid {BORDER_COLOR}; border-radius:8px; padding:9px; font-size:10px; }}
    QLabel[role="panelTitle"] {{ color:{TEXT_COLOR}; font-size:11px; font-weight:700; background:transparent; border:0; }}
    QLabel[role="cardTitle"] {{ color:{TEXT_COLOR}; font-size:10px; font-weight:700; background:transparent; border:0; }}
    QLabel[role="cardValue"] {{ color:{TEXT_COLOR}; font-size:15px; font-weight:700; background:transparent; border:0; }}
    QLabel[role="cardDetail"] {{ color:{SECONDARY_TEXT}; font-size:9px; background:transparent; border:0; }}
    QLabel[role="positive"] {{ color:{PRIMARY_COLOR}; }}
    QLabel[role="negative"] {{ color:{ERROR_COLOR}; }}
    QLabel[role="statusDot"] {{ background:{PRIMARY_COLOR}; border:0; border-radius:3px; }}
    QLabel[role="iconBadge"] {{ background:#112633; border:1px solid {BORDER_COLOR}; border-radius:7px; }}
    QFrame[role="separator"] {{ background:{BORDER_COLOR}; border:0; }}
    QFrame[role="panel"], QWidget[role="panel"], QGroupBox {{ background:{CARD_COLOR}; border:1px solid {BORDER_COLOR}; border-radius:8px; }}
    QFrame[role="card"], QWidget[role="card"], QLabel[role="metricCard"] {{ background:{CARD_COLOR}; border:1px solid {BORDER_COLOR}; border-radius:8px; }}
    QLabel[role="metricCard"] {{ padding:8px; color:{TEXT_COLOR}; font-weight:600; }}
    QGroupBox {{ margin-top:10px; padding:12px 10px 8px; font-weight:700; }}
    QGroupBox::title {{ subcontrol-origin:margin; left:10px; padding:0 4px; }}
    QFrame#KpiCard {{ background:rgba(10,25,37,225); border:1px solid {BORDER_COLOR}; border-top:2px solid {PRIMARY_COLOR}; border-radius:8px; }}
    QFrame#KpiCard[accent="info"] {{ border-top-color:{INFO_COLOR}; }}
    QFrame#KpiCard[accent="warning"] {{ border-top-color:{WARNING_COLOR}; }}
    QFrame#KpiCard[accent="danger"] {{ border-top-color:{ERROR_COLOR}; }}
    QFrame#KpiCard[accent="purple"] {{ border-top-color:#B64CFF; }}
    QWidget[role="toolbar"] {{ background:transparent; border:0; }}
    QToolBar {{ background:{PANEL_COLOR}; border:0; border-bottom:1px solid {BORDER_COLOR}; spacing:6px; padding:5px; }}
    QToolButton {{ background:#111820; color:#F4F7FA; border:1px solid #263442; border-radius:4px; padding:4px 7px; font-size:9px; font-weight:600; }}
    QToolButton:hover {{ background:#1B2A35; border-color:#00C853; }}
    QToolButton:pressed {{ background:#123422; }}
    QStatusBar {{ background:{PANEL_COLOR}; border-top:1px solid {BORDER_COLOR}; color:{SECONDARY_TEXT}; }}
    QListWidget {{ background:{PANEL_COLOR}; border:0; outline:0; padding:8px; }}
    QListWidget::item {{ border-radius:6px; margin:0; padding:2px 8px; color:{SECONDARY_TEXT}; font-size:10px; }}
    QListWidget::item:selected {{ background:#17422F; color:{TEXT_COLOR}; border-left:3px solid {PRIMARY_COLOR}; }}
    QListWidget::item:hover {{ background:#303744; color:{TEXT_COLOR}; }}
    QDockWidget {{ color:{TEXT_COLOR}; font-weight:600; }}
    QDockWidget::title {{ background:{PANEL_COLOR}; border-bottom:1px solid {BORDER_COLOR}; padding:7px; }}
    QDialog {{ background:{BACKGROUND_COLOR}; color:{TEXT_COLOR}; }}
    QDialog QLabel {{ background:transparent; color:{TEXT_COLOR}; }}
    QDialog QTabWidget::pane {{ background:{BACKGROUND_COLOR}; border:1px solid {BORDER_COLOR}; top:-1px; }}
    QDialog QTabBar::tab {{ background:#101C27; color:#AEBCC8; border:1px solid {BORDER_COLOR}; border-bottom:0; border-top-left-radius:5px; border-top-right-radius:5px; padding:7px 12px; margin-right:2px; font-size:10px; font-weight:600; }}
    QDialog QTabBar::tab:selected {{ background:#173041; color:#F4F7FA; border-top:2px solid {PRIMARY_COLOR}; }}
    QDialog QTabBar::tab:hover:!selected {{ background:#1A2A36; color:#EAF1F5; }}
    QDialog #SectionWidget {{ background:#091720; border:1px solid {BORDER_COLOR}; border-radius:7px; }}
    QDialog #SectionTitle {{ color:#EAF1F5; font-size:12px; font-weight:700; }}
    QDialog QLineEdit, QDialog QTextEdit, QDialog QPlainTextEdit, QDialog QComboBox, QDialog QSpinBox, QDialog QDoubleSpinBox {{ background:#071119; color:#EAF1F5; border:1px solid #355065; border-radius:4px; padding:4px 6px; selection-background-color:#1E4F78; }}
    QDialog QLineEdit:focus, QDialog QTextEdit:focus, QDialog QComboBox:focus, QDialog QSpinBox:focus, QDialog QDoubleSpinBox:focus {{ border-color:{PRIMARY_COLOR}; }}
    QPushButton {{ background:#18242F; color:{TEXT_COLOR}; border:1px solid {BORDER_COLOR}; border-radius:6px; padding:6px 10px; font-size:10px; font-weight:600; }}
    QPushButton:hover {{ background:#243746; border-color:{PRIMARY_COLOR}; }}
    QPushButton:pressed, QPushButton:checked {{ background:#17422F; border-color:{PRIMARY_COLOR}; color:#FFFFFF; }}
    QPushButton:disabled {{ background:#202832; border-color:#2A3440; color:#6F7C87; }}
    QPushButton[variant="danger"] {{ color:#FF7B86; }} QPushButton[variant="danger"]:hover {{ background:#3A2027; border-color:{ERROR_COLOR}; }}
    QPushButton[variant="success"] {{ color:{PRIMARY_COLOR}; }}
    QPushButton[variant="info"] {{ color:{INFO_COLOR}; }}
    QPushButton[variant="warning"] {{ color:{WARNING_COLOR}; }}
    QPushButton[variant="purple"] {{ color:#D279FF; }}
    QPushButton[variant="compact"] {{ padding:3px 7px; font-size:9px; }}
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{ background:#0B1721; color:{TEXT_COLOR}; border:1px solid #355065; border-radius:6px; padding:5px 7px; selection-background-color:#1E4F78; }}
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover {{ border-color:#527087; }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{ border-color:{PRIMARY_COLOR}; }}
    QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled {{ background:#202832; color:#6F7C87; border-color:#2A3440; }}
    QLineEdit[role="search"] {{ padding-left:9px; border-color:#3A566B; }}
    QComboBox::drop-down {{ border:0; width:20px; }}
    QComboBox QAbstractItemView {{ background:{PANEL_COLOR}; color:{TEXT_COLOR}; border:1px solid {BORDER_COLOR}; selection-background-color:#17422F; }}
    QComboBox[variant="purple"] {{ color:#D279FF; border-color:#7C3AAD; }}
    QPushButton[calendarState="positive"], QLabel[calendarState="positive"] {{ background:#123A2A; color:#7DFFB3; }}
    QPushButton[calendarState="negative"], QLabel[calendarState="negative"] {{ background:#3A2027; color:#FF9AA3; }}
    QPushButton[calendarState="neutral"], QLabel[calendarState="neutral"] {{ background:{CARD_COLOR}; color:{TEXT_COLOR}; }}
    QPushButton[calendarSelected="true"] {{ border:2px solid {INFO_COLOR}; }}
    QPushButton[calendarCurrent="true"] {{ border:2px solid {WARNING_COLOR}; }}
    QScrollBar:vertical {{ background:transparent; width:8px; margin:5px 2px; }}
    QScrollBar::handle:vertical {{ background:#355065; min-height:30px; border-radius:4px; }}
    QScrollBar::handle:vertical:hover {{ background:#00A968; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; background:transparent; border:0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background:transparent; }}
    QScrollBar:horizontal {{ background:transparent; height:8px; margin:2px 5px; }}
    QScrollBar::handle:horizontal {{ background:#355065; min-width:30px; border-radius:4px; }}
    QScrollBar::handle:horizontal:hover {{ background:#00A968; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width:0; background:transparent; border:0; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background:transparent; }}
    {table_style()}
    QTableView, QTableWidget {{ font-size:10px; }}
    QTableView::item, QTableWidget::item {{ padding:2px 5px; }}
    QHeaderView::section {{ padding:3px 6px; font-size:9px; }}
    """


def apply_terminal_palette(application=None):
    """Set Qt palette roles so native delegates never fall back to light cells."""
    application = application or QApplication.instance()
    if application is None:
        return
    palette = application.palette()
    palette.setColor(QPalette.Window, QColor(BACKGROUND_COLOR))
    palette.setColor(QPalette.Base, QColor(CARD_COLOR))
    palette.setColor(QPalette.AlternateBase, QColor("#292F39"))
    palette.setColor(QPalette.Text, QColor(TEXT_COLOR))
    palette.setColor(QPalette.WindowText, QColor(TEXT_COLOR))
    palette.setColor(QPalette.Highlight, QColor("#1E4F78"))
    palette.setColor(QPalette.HighlightedText, QColor(TEXT_COLOR))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor("#AAB3BE"))
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#AAB3BE"))
    palette.setColor(QPalette.Disabled, QPalette.Base, QColor("#242A33"))
    application.setPalette(palette)


def configure_active_tables(root):
    """Apply the professional table contract to every table under ``root``."""
    for table in root.findChildren(QTableView):
        configure_professional_table(table)


def configure_professional_table(table, auto_size=True):
    """Configure one compact, sortable, user-resizable enterprise table."""
    table.setProperty("enterpriseTable", True)
    table.setAlternatingRowColors(True)
    table.setMouseTracking(True)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setShowGrid(False)
    table.setWordWrap(False)
    table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
    table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
    if hasattr(table, "setSortingEnabled"):
        table.setSortingEnabled(True)
    vertical = table.verticalHeader()
    vertical.setVisible(False)
    vertical.setMinimumSectionSize(28)
    vertical.setDefaultSectionSize(28)
    vertical.setSectionResizeMode(QHeaderView.Fixed)
    header = table.horizontalHeader()
    header.setProperty("stickyHeader", True)
    header.setProperty("stickyHeader", True)
    header.setProperty("stickyHeader", True)
    header.setVisible(True)
    header.setFixedHeight(32)
    header.setMinimumSectionSize(48)
    header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    header.setStretchLastSection(False)
    header.setSectionsClickable(True)
    header.setSectionsMovable(False)
    header.setSectionResizeMode(QHeaderView.Interactive)
    if auto_size:
        QTimer.singleShot(0, table.resizeColumnsToContents)


class _EnterpriseHoverAnimator(QObject):
    """Small centralized hover fade shared by all enterprise controls."""

    def eventFilter(self, watched, event):
        if event.type() not in (QEvent.Enter, QEvent.Leave) or not watched.isEnabled():
            return False
        animation = QPropertyAnimation(watched, b"windowOpacity", watched)
        animation.setDuration(90)
        animation.setStartValue(watched.windowOpacity())
        animation.setEndValue(0.94 if event.type() == QEvent.Enter else 1.0)
        animation.start(QPropertyAnimation.DeleteWhenStopped)
        return False


_hover_animator = _EnterpriseHoverAnimator()


def set_visual_role(widget, role=None, variant=None):
    """Assign semantic theme roles without local stylesheets."""
    if role:
        widget.setProperty("role", role)
    if variant:
        widget.setProperty("variant", variant)
    refresh_widget_style(widget)
    return widget


def refresh_widget_style(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def apply_standard_components(root):
    """Normalize controls, states, shadows and interaction across a page."""
    from dashboard.icons import apply_standard_icons

    apply_standard_icons(root)
    for button in root.findChildren(QPushButton):
        button.installEventFilter(_hover_animator)
    for line_edit in root.findChildren(QLineEdit):
        name = line_edit.objectName().lower()
        if "search" in name or "buscar" in line_edit.placeholderText().lower():
            line_edit.setProperty("role", "search")
    for group in root.findChildren(QGroupBox):
        group.setProperty("role", "panel")
    for frame in root.findChildren(QFrame):
        if frame.property("role") in ("panel", "card") and frame.graphicsEffect() is None:
            shadow = QGraphicsDropShadowEffect(frame)
            shadow.setBlurRadius(14)
            shadow.setOffset(0, 2)
            shadow.setColor(QColor(0, 0, 0, 90))
            frame.setGraphicsEffect(shadow)
    configure_active_tables(root)


def status_chip(color):
    return f"background:{CARD_COLOR}; color:{color}; border:1px solid {BORDER_COLOR}; border-radius:11px; padding:3px 7px; font-size:9px; font-weight:600;"


def dashboard_card(accent=PRIMARY_COLOR):
    return f"background:{CARD_COLOR}; border:1px solid {BORDER_COLOR}; border-top:3px solid {accent}; border-radius:8px;"


POSITIVE, NEGATIVE, WARNING = PRIMARY_COLOR, ERROR_COLOR, WARNING_COLOR
