"""Single-source Lucide icon system for the Enterprise interface."""

from functools import lru_cache
from pathlib import Path

import re

from PySide6.QtCore import QByteArray, QEvent, QObject, QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication, QAbstractButton, QDialog, QHBoxLayout, QLabel,
                               QListWidget, QToolBar, QWidget)


_ICON_ROOT = Path(__file__).resolve().parent.parent / "assets" / "icons" / "lucide"
ICON_SIZE = 16
ICON_SIZE_COMPACT = 14
ICON_SIZE_CARD = 24
ICON_COLOR = "#C7D2DC"
ICON_MUTED = "#8D9CAA"
ICON_SUCCESS = "#00C853"
ICON_DANGER = "#FF4D5E"
ICON_INFO = "#45A3FF"

_SEMANTIC_ICONS = (
    (("guardar", "save"), "circle-check", ICON_SUCCESS),
    (("cancelar", "cerrar", "close"), "square", ICON_MUTED),
    (("eliminar", "borrar", "delete", "reiniciar"), "square", ICON_DANGER),
    (("actualizar", "refrescar", "sync", "sincronizar"), "refresh-cw", ICON_INFO),
    (("buscar", "search", "inspector"), "search-check", ICON_INFO),
    (("nuevo", "nueva", "agregar", "crear"), "user-round", ICON_SUCCESS),
    (("editar", "configur", "ajustes"), "settings", ICON_COLOR),
    (("activar", "iniciar", "play", "cargar"), "play", ICON_SUCCESS),
    (("desactivar", "detener", "stop", "desconectar"), "square", ICON_DANGER),
    (("probar", "diagnóstico", "verificar", "certificación"), "circle-check", ICON_INFO),
    (("exportar", "reporte", "json", "txt", "csv", "pdf"), "folder-open", ICON_COLOR),
    (("importar", "restaurar"), "folder-open", ICON_INFO),
    (("backup", "respaldo"), "database-backup", ICON_COLOR),
    (("perfil", "usuario"), "users", ICON_COLOR),
    (("telegram", "canal"), "send", ICON_INFO),
    (("mt5", "trading", "operación"), "briefcase-business", ICON_COLOR),
    (("analítica", "estadística", "mercado", "mapa"), "chart-spline", ICON_INFO),
    (("calendario", "hoy", "anterior", "siguiente"), "calendar-days", ICON_COLOR),
    (("notificacion", "aviso"), "radio", ICON_INFO),
    (("duplicar", "copiar"), "list-checks", ICON_COLOR),
)


@lru_cache(maxsize=256)
def colored_icon(name: str, color: str = "#D7E2EA") -> QIcon:
    """Return a high-resolution local SVG icon rendered in the requested colour."""
    path = _ICON_ROOT / f"{name}.svg"
    if not path.exists():
        return QIcon()
    svg = path.read_text(encoding="utf-8").replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(96, 96)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def semantic_icon(text: str) -> QIcon:
    """Resolve a control label to the shared Lucide visual vocabulary."""
    normalized = re.sub(r"[^a-záéíóúüñ0-9 ]", "", (text or "").lower())
    for terms, name, color in _SEMANTIC_ICONS:
        if any(term in normalized for term in terms):
            return colored_icon(name, color)
    return QIcon()


def set_label_icon(label: QLabel, name: str, color: str = ICON_COLOR, size: int = ICON_SIZE):
    label.setText("")
    label.setPixmap(colored_icon(name, color).pixmap(size, size))
    label.setFixedSize(size, size)
    label.setAlignment(Qt.AlignCenter)
    label.setProperty("enterpriseIcon", True)


def icon_chip(label: QLabel, name: str, color: str) -> QWidget:
    """Wrap a live text label in the standard icon-bearing status chip."""
    chip = QWidget()
    chip.setProperty("enterpriseIconChip", True)
    layout = QHBoxLayout(chip)
    layout.setContentsMargins(7, 2, 7, 2)
    layout.setSpacing(5)
    glyph = QLabel()
    set_label_icon(glyph, name, color, ICON_SIZE_COMPACT)
    label.setStyleSheet(
        f"background:transparent;border:0;padding:0;color:{color};"
        "font-family:'Segoe UI';font-size:9px;font-weight:600;"
    )
    layout.addWidget(glyph)
    layout.addWidget(label)
    return chip


def apply_standard_icons(root: QWidget):
    """Normalize icons on every supported control below ``root``."""
    buttons = ([root] if isinstance(root, QAbstractButton) else []) + root.findChildren(QAbstractButton)
    for button in buttons:
        if button.property("calendarState") is not None:
            continue
        if button.icon().isNull():
            icon = semantic_icon(button.text())
            if not icon.isNull():
                button.setIcon(icon)
        button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        button.setProperty("enterpriseIcon", True)
    for toolbar in root.findChildren(QToolBar):
        toolbar.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
    for navigation in root.findChildren(QListWidget):
        if navigation.objectName() == "EnterpriseNavigation" or navigation.property("enterpriseNavigation"):
            navigation.setIconSize(QSize(ICON_SIZE, ICON_SIZE))


class _IconSystem(QObject):
    def eventFilter(self, watched, event):
        if event.type() == QEvent.Show and isinstance(watched, QDialog):
            QTimer.singleShot(0, lambda widget=watched: apply_standard_icons(widget))
        return False


_icon_system = _IconSystem()


def install_icon_system(application=None):
    """Apply Lucide consistently, including dialogs created later."""
    application = application or QApplication.instance()
    if application is not None and not application.property("enterpriseIconSystem"):
        application.installEventFilter(_icon_system)
        application.setProperty("enterpriseIconSystem", True)
