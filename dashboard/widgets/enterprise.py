"""Reusable, presentation-only components for Kraken Bot Enterprise."""
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QTableWidget,
                               QToolButton, QVBoxLayout, QWidget)
from dashboard.styles import (BORDER_COLOR, CARD_COLOR, ERROR_COLOR, PRIMARY_COLOR,
                              SECONDARY_TEXT, TEXT_COLOR, WARNING_COLOR)
from dashboard.widgets.metric_card import MetricCard
from dashboard.widgets.status_badge import StatusBadge


class StatCard(QFrame):
    def __init__(self, title, value="—", detail="", color=PRIMARY_COLOR, parent=None):
        super().__init__(parent); self.setObjectName("EnterpriseStatCard")
        self.setStyleSheet(f"#EnterpriseStatCard{{background:{CARD_COLOR};border:1px solid {BORDER_COLOR};border-left:3px solid {color};border-radius:9px;}}")
        box=QVBoxLayout(self); box.setContentsMargins(12,9,12,9); box.setSpacing(2)
        self.title=QLabel(title.upper()); self.title.setStyleSheet(f"color:{SECONDARY_TEXT};font-size:10px;font-weight:700;")
        self.value=QLabel(str(value)); self.value.setStyleSheet(f"color:{color};font-size:21px;font-weight:700;")
        self.detail=QLabel(detail); self.detail.setStyleSheet(f"color:{SECONDARY_TEXT};font-size:10px;")
        box.addWidget(self.title); box.addWidget(self.value); box.addWidget(self.detail)
    def set_value(self, value, detail=None):
        self.value.setText(str(value));
        if detail is not None: self.detail.setText(str(detail))


class EmptyState(QFrame):
    def __init__(self, module, guidance, parent=None):
        super().__init__(parent); self.setStyleSheet(f"background:{CARD_COLOR};border:1px dashed {BORDER_COLOR};border-radius:8px;")
        box=QVBoxLayout(self); box.setContentsMargins(15,12,15,12)
        title=QLabel(f"{module}: sin datos todavía"); title.setStyleSheet(f"color:{TEXT_COLOR};font-weight:700;")
        help_text=QLabel(guidance); help_text.setWordWrap(True); help_text.setStyleSheet(f"color:{SECONDARY_TEXT};")
        box.addWidget(title); box.addWidget(help_text)


class LoadingOverlay(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent); self.setStyleSheet("background:rgba(27,29,34,205);border-radius:8px;"); self.hide()
        box=QVBoxLayout(self); label=QLabel("Actualizando datos…"); label.setAlignment(Qt.AlignCenter); label.setStyleSheet(f"color:{TEXT_COLOR};font-weight:700;"); box.addWidget(label)
    def set_loading(self, value): self.setVisible(value)


class EnterpriseTable(QTableWidget):
    """Drop-in table with persistent column layout; legacy tables are upgraded below."""
    def __init__(self, key="table", parent=None): super().__init__(parent); configure_enterprise_table(self, key)


class EnterpriseToolbar(QWidget):
    def __init__(self, title, icon="◆", parent=None):
        super().__init__(parent); box=QHBoxLayout(self); box.setContentsMargins(0,0,0,4)
        heading=QLabel(f"{icon}  {title}"); heading.setStyleSheet(f"color:{TEXT_COLOR};font-size:18px;font-weight:700;"); box.addWidget(heading); box.addStretch()


class EnterpriseFilterBar(QWidget):
    def __init__(self, parent=None): super().__init__(parent); self.layout=QHBoxLayout(self); self.layout.setContentsMargins(0,0,0,0); self.layout.setSpacing(7)
    def add_filter(self, widget): self.layout.addWidget(widget)


class EnterpriseSection(QFrame):
    def __init__(self, title, subtitle="", parent=None):
        super().__init__(parent); self.setStyleSheet(f"background:{CARD_COLOR};border:1px solid {BORDER_COLOR};border-radius:9px;")
        box=QVBoxLayout(self); box.setContentsMargins(12,9,12,9)
        head=QLabel(title); head.setStyleSheet(f"color:{TEXT_COLOR};font-weight:700;font-size:14px;"); sub=QLabel(subtitle); sub.setStyleSheet(f"color:{SECONDARY_TEXT};"); sub.setWordWrap(True); box.addWidget(head); box.addWidget(sub)


class EnterpriseChart(QWidget):
    def __init__(self, title="Rendimiento", parent=None): super().__init__(parent); self.title=title; self.values=[]; self.setMinimumHeight(140)
    def set_values(self, values): self.values=list(values); self.update()
    def paintEvent(self, event):
        p=QPainter(self); p.fillRect(self.rect(), QColor(CARD_COLOR)); p.setPen(QColor(SECONDARY_TEXT)); p.drawText(10,20,self.title); p.setPen(QPen(QColor(BORDER_COLOR),1)); p.drawLine(10,self.height()-22,self.width()-10,self.height()-22)
        if self.values:
            maximum=max(max(map(abs,self.values)),1); p.setPen(QPen(QColor(PRIMARY_COLOR),2)); last=None
            for i,value in enumerate(self.values):
                point=(12+i*(self.width()-24)/max(1,len(self.values)-1), self.height()-24-value/maximum*(self.height()-45))
                if last: p.drawLine(*last,*point)
                last=point


def configure_enterprise_table(table, key=None):
    key = key or table.objectName() or f"{table.parent().__class__.__name__}_{id(table)}"
    table.setObjectName(key); table.setAlternatingRowColors(True); table.setMouseTracking(True); table.setSortingEnabled(True)
    settings=QSettings("KrakenBot", "EnterpriseUI"); widths=settings.value(f"tables/{key}/widths")
    if widths:
        for index,width in enumerate(widths): table.setColumnWidth(index, int(width))
    def save_layout(*_): settings.setValue(f"tables/{key}/widths", [table.columnWidth(i) for i in range(table.columnCount())])
    table.horizontalHeader().sectionResized.connect(save_layout)


def decorate_enterprise_page(page, title, guidance):
    """Upgrade legacy page presentation while keeping its widgets and commands intact."""
    if getattr(page, "_enterprise_decorated", False): return
    layout=page.layout()
    if layout:
        layout.insertWidget(0, EnterpriseToolbar(title))
        layout.insertWidget(1, EnterpriseSection("Centro de trabajo", guidance))
    for index,table in enumerate(page.findChildren(QTableWidget)):
        configure_enterprise_table(table, f"{page.__class__.__name__}_{index}")
    page._enterprise_decorated=True
