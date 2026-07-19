"""Visual identity helpers. SVG is preferred; a raster QPixmap is the DPI-safe fallback."""
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from version import APPLICATION_NAME, COPYRIGHT, RELEASE_CHANNEL, VERSION

ROOT = Path(__file__).resolve().parent.parent
LOGO_SVG = ROOT / "assets" / "branding" / "kraken_bot_logo.svg"
LOGO_PNG = ROOT / "assets" / "branding" / "kraken_bot_logo.png"

def application_icon():
    return QIcon(str(LOGO_PNG if LOGO_PNG.exists() else LOGO_SVG))

def logo_pixmap(size=96):
    """Render a DPI-safe raster fallback for Qt surfaces that cannot paint SVG."""
    pixmap = application_icon().pixmap(size, size)
    if not pixmap.isNull(): return pixmap
    fallback = QPixmap(size, size); fallback.fill(Qt.transparent); painter = QPainter(fallback); painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor("#1B1D22")); painter.setPen(QColor("#00C853")); painter.drawRoundedRect(2, 2, size-4, size-4, size//5, size//5)
    painter.setPen(QColor("#00E676")); painter.setFont(QFont("Segoe UI", max(10, size//3), QFont.Bold)); painter.drawText(fallback.rect(), Qt.AlignCenter, "K"); painter.end(); return fallback

def splash_pixmap():
    pixmap = QPixmap(560, 300); pixmap.fill(QColor("#1B1D22")); painter = QPainter(pixmap); painter.setRenderHint(QPainter.Antialiasing)
    painter.drawPixmap(48, 70, logo_pixmap(128)); painter.setPen(QColor("#FFFFFF")); painter.setFont(QFont("Segoe UI", 25, QFont.Bold)); painter.drawText(205, 125, APPLICATION_NAME)
    painter.setPen(QColor("#00C853")); painter.setFont(QFont("Segoe UI", 12, QFont.DemiBold)); painter.drawText(207, 155, f"{RELEASE_CHANNEL}  ·  v{VERSION}")
    painter.setPen(QColor("#B0BEC5")); painter.setFont(QFont("Segoe UI", 10)); painter.drawText(207, 188, COPYRIGHT); painter.end(); return pixmap
