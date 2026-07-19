"""Centralized terminal-style theme for the Kraken Bot shell and dashboard."""
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QTableView

from dashboard.styles import (ACCENT_COLOR, BACKGROUND_COLOR, BORDER_COLOR, CARD_COLOR,
                              ERROR_COLOR, PANEL_COLOR, PRIMARY_COLOR, SECONDARY_TEXT,
                              TEXT_COLOR, WARNING_COLOR, table_style)


def application_style():
    return f"""
    QMainWindow, QWidget {{ background:{BACKGROUND_COLOR}; font-family:'Segoe UI'; font-size:12px; }}
    QToolBar {{ background:{PANEL_COLOR}; border:0; border-bottom:1px solid {BORDER_COLOR}; spacing:6px; padding:5px; }}
    QStatusBar {{ background:{PANEL_COLOR}; border-top:1px solid {BORDER_COLOR}; color:{SECONDARY_TEXT}; }}
    QListWidget {{ background:{PANEL_COLOR}; border:0; outline:0; padding:8px; }}
    QListWidget::item {{ border-radius:7px; margin:2px 0; padding:9px 10px; color:{SECONDARY_TEXT}; }}
    QListWidget::item:selected {{ background:#17422F; color:{TEXT_COLOR}; border-left:3px solid {PRIMARY_COLOR}; }}
    QListWidget::item:hover {{ background:#303744; color:{TEXT_COLOR}; }}
    QDockWidget {{ color:{TEXT_COLOR}; font-weight:600; }}
    QDockWidget::title {{ background:{PANEL_COLOR}; border-bottom:1px solid {BORDER_COLOR}; padding:7px; }}
    QPushButton {{ background:#353C49; color:{TEXT_COLOR}; border:1px solid {BORDER_COLOR}; border-radius:6px; padding:7px 10px; }}
    QPushButton:hover {{ background:#424C5C; }} QPushButton:pressed {{ background:#1C6B45; }}
    {table_style()}
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
    """Enable shared readability behaviour without changing page business logic."""
    for table in root.findChildren(QTableView):
        table.setAlternatingRowColors(True)
        table.setMouseTracking(True)


def status_chip(color):
    return f"background:{CARD_COLOR}; color:{color}; border:1px solid {BORDER_COLOR}; border-radius:9px; padding:5px 9px; font-weight:600;"


def dashboard_card(accent=PRIMARY_COLOR):
    return f"background:{CARD_COLOR}; border:1px solid {BORDER_COLOR}; border-top:3px solid {accent}; border-radius:8px;"


POSITIVE, NEGATIVE, WARNING = PRIMARY_COLOR, ERROR_COLOR, WARNING_COLOR
