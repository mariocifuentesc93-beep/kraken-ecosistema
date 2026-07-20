"""Reusable, presentation-only components for Kraken Bot Enterprise."""

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from dashboard.icons import colored_icon
from dashboard.ui_theme import apply_standard_components, set_visual_role
from dashboard.styles import (
    BORDER_COLOR,
    CARD_COLOR,
    PRIMARY_COLOR,
    SECONDARY_TEXT,
    TEXT_COLOR,
)


class StatCard(QFrame):
    def __init__(self, title, value="—", detail="", color=PRIMARY_COLOR, parent=None):
        super().__init__(parent)
        self.setObjectName("EnterpriseStatCard")
        set_visual_role(self, "card")
        box = QVBoxLayout(self)
        box.setContentsMargins(12, 9, 12, 9)
        box.setSpacing(2)
        self.title = QLabel(title.upper())
        set_visual_role(self.title, "cardTitle")
        self.value = QLabel(str(value))
        set_visual_role(self.value, "cardValue")
        self.detail = QLabel(detail)
        set_visual_role(self.detail, "cardDetail")
        box.addWidget(self.title)
        box.addWidget(self.value)
        box.addWidget(self.detail)

    def set_value(self, value, detail=None):
        self.value.setText(str(value))
        if detail is not None:
            self.detail.setText(str(detail))


class EmptyState(QFrame):
    """A calm, reusable empty state for modules without records yet."""

    def __init__(self, module, guidance, icon_name="chart-spline", parent=None):
        super().__init__(parent)
        self.setObjectName("EnterpriseEmptyState")
        set_visual_role(self, "panel")
        box = QVBoxLayout(self)
        box.setContentsMargins(18, 14, 18, 14)
        box.setSpacing(4)
        icon = QLabel()
        icon.setAlignment(Qt.AlignCenter)
        icon.setPixmap(colored_icon(icon_name, "#607080").pixmap(24, 24))
        title = QLabel(module)
        title.setAlignment(Qt.AlignCenter)
        set_visual_role(title, "panelTitle")
        help_text = QLabel(guidance)
        help_text.setAlignment(Qt.AlignCenter)
        help_text.setWordWrap(True)
        set_visual_role(help_text, "subtitle")
        box.addWidget(icon)
        box.addWidget(title)
        box.addWidget(help_text)


class LoadingOverlay(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        set_visual_role(self, "panel")
        self.hide()
        box = QVBoxLayout(self)
        label = QLabel("Actualizando datos…")
        label.setAlignment(Qt.AlignCenter)
        set_visual_role(label, "panelTitle")
        box.addWidget(label)

    def set_loading(self, value):
        self.setVisible(value)


class EnterpriseTable(QTableWidget):
    """Drop-in table with readable dark styling and persistent column layout."""

    def __init__(self, key="table", parent=None):
        super().__init__(parent)
        configure_enterprise_table(self, key)


class EnterpriseToolbar(QWidget):
    def __init__(self, title, icon="◆", parent=None):
        super().__init__(parent)
        box = QHBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 4)
        heading = QLabel(f"{icon}  {title}")
        set_visual_role(heading, "pageTitle")
        box.addWidget(heading)
        box.addStretch()


class EnterpriseIconToolbar(QFrame):
    """Compact page heading with the matching sidebar icon and a useful subtitle."""

    def __init__(self, title, icon_name, parent=None):
        super().__init__(parent)
        self.setObjectName("EnterprisePageHeader")
        set_visual_role(self, "panel")
        self.setMinimumHeight(64)
        self.setMaximumHeight(70)
        box = QHBoxLayout(self)
        box.setContentsMargins(14, 10, 14, 10)
        box.setSpacing(10)
        glyph = QLabel()
        glyph.setFixedSize(30, 30)
        glyph.setAlignment(Qt.AlignCenter)
        set_visual_role(glyph, "iconBadge")
        glyph.setPixmap(colored_icon(icon_name, PRIMARY_COLOR).pixmap(18, 18))
        text_box = QVBoxLayout()
        text_box.setContentsMargins(0, 0, 0, 0)
        text_box.setSpacing(1)
        heading = QLabel(title)
        set_visual_role(heading, "pageTitle")
        self.guidance = QLabel()
        set_visual_role(self.guidance, "subtitle")
        text_box.addWidget(heading)
        text_box.addWidget(self.guidance)
        box.addWidget(glyph)
        box.addLayout(text_box)
        box.addStretch()

    def set_guidance(self, guidance):
        self.guidance.setText(guidance)


class EnterpriseFilterBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        set_visual_role(self, "toolbar")
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(7)

    def add_filter(self, widget):
        self.layout.addWidget(widget)


class EnterpriseSection(QFrame):
    def __init__(self, title, subtitle="", parent=None):
        super().__init__(parent)
        set_visual_role(self, "panel")
        box = QVBoxLayout(self)
        box.setContentsMargins(12, 9, 12, 9)
        head = QLabel(title)
        set_visual_role(head, "panelTitle")
        sub = QLabel(subtitle)
        set_visual_role(sub, "subtitle")
        sub.setWordWrap(True)
        box.addWidget(head)
        box.addWidget(sub)


class EnterpriseChart(QWidget):
    def __init__(self, title="Rendimiento", parent=None):
        super().__init__(parent)
        self.title = title
        self.values = []
        self.setMinimumHeight(140)

    def set_values(self, values):
        self.values = list(values)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(CARD_COLOR))
        painter.setPen(QColor(SECONDARY_TEXT))
        painter.drawText(10, 20, self.title)
        painter.setPen(QPen(QColor(BORDER_COLOR), 1))
        painter.drawLine(10, self.height() - 22, self.width() - 10, self.height() - 22)
        if self.values:
            maximum = max(max(map(abs, self.values)), 1)
            painter.setPen(QPen(QColor(PRIMARY_COLOR), 2))
            last = None
            for index, value in enumerate(self.values):
                point = (
                    12 + index * (self.width() - 24) / max(1, len(self.values) - 1),
                    self.height() - 24 - value / maximum * (self.height() - 45),
                )
                if last:
                    painter.drawLine(*last, *point)
                last = point


def configure_enterprise_table(table, key=None):
    """Apply shared table behavior without touching model or repository code."""
    key = key or table.objectName() or f"{table.parent().__class__.__name__}_{id(table)}"
    table.setObjectName(key)
    table.setAlternatingRowColors(True)
    table.setMouseTracking(True)
    table.setSortingEnabled(True)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setShowGrid(False)
    table.setWordWrap(False)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(30)
    header = table.horizontalHeader()
    header.setMinimumHeight(34)
    header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    header.setSectionResizeMode(QHeaderView.Interactive)
    settings = QSettings("KrakenBot", "EnterpriseUI")
    widths = settings.value(f"tables/{key}/widths")
    if widths:
        for index, width in enumerate(widths):
            table.setColumnWidth(index, int(width))

    def save_layout(*_):
        settings.setValue(
            f"tables/{key}/widths",
            [table.columnWidth(index) for index in range(table.columnCount())],
        )

    header.sectionResized.connect(save_layout)


def decorate_enterprise_page(page, title, guidance, icon_name="circle-check"):
    """Upgrade a legacy page visually while preserving its commands and content."""
    if getattr(page, "_enterprise_decorated", False):
        return
    layout = page.layout()
    if layout:
        header = EnterpriseIconToolbar(title, icon_name)
        header.set_guidance(guidance)
        layout.insertWidget(0, header)
    for index, table in enumerate(page.findChildren(QTableWidget)):
        configure_enterprise_table(table, f"{page.__class__.__name__}_{index}")
    from dashboard.layout_manager import enterprise_layout
    enterprise_layout.configure_page(page)
    apply_standard_components(page)
    page._enterprise_decorated = True
