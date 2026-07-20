"""Animated, keyboard-friendly Enterprise navigation components."""

from PySide6.QtCore import QEasingCurve, Qt, Signal, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QKeyEvent, QPainter, QPen
from PySide6.QtWidgets import QListWidget, QStyle, QStyleOptionViewItem, QStyledItemDelegate


GROUP_ROLE = Qt.UserRole + 1
FULL_TEXT_ROLE = Qt.UserRole + 2


class EnterpriseNavigationList(QListWidget):
    """List with smooth hover/selection feedback and predictable keyboard movement."""

    group_toggle_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.hover_row = -1
        self.hover_progress = 0.0
        self.previous_row = -1
        self.selection_progress = 1.0
        self.itemEntered.connect(self._start_hover)
        self.currentRowChanged.connect(self._start_selection)
        self._hover_animation = QVariantAnimation(self)
        self._hover_animation.setDuration(140)
        self._hover_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._hover_animation.valueChanged.connect(self._set_hover_progress)
        self._selection_animation = QVariantAnimation(self)
        self._selection_animation.setDuration(180)
        self._selection_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._selection_animation.valueChanged.connect(self._set_selection_progress)

    def leaveEvent(self, event):
        self.hover_row = -1
        self.hover_progress = 0.0
        self.viewport().update()
        super().leaveEvent(event)

    def _start_hover(self, item):
        self.hover_row = self.row(item)
        self._hover_animation.stop()
        self._hover_animation.setStartValue(0.0)
        self._hover_animation.setEndValue(1.0)
        self._hover_animation.start()

    def _start_selection(self, row):
        if row == self.previous_row:
            return
        self.previous_row = getattr(self, "selected_row", -1)
        self.selected_row = row
        self._selection_animation.stop()
        self._selection_animation.setStartValue(0.0)
        self._selection_animation.setEndValue(1.0)
        self._selection_animation.start()

    def _set_hover_progress(self, value):
        self.hover_progress = float(value)
        self.viewport().update()

    def _set_selection_progress(self, value):
        self.selection_progress = float(value)
        self.viewport().update()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            item = self.currentItem()
            if item is not None and item.data(Qt.UserRole) == -1:
                self.group_toggle_requested.emit(item)
                return
        if event.key() in (Qt.Key_Down, Qt.Key_Up, Qt.Key_Home, Qt.Key_End):
            direction = 1 if event.key() in (Qt.Key_Down, Qt.Key_Home) else -1
            start = -1 if event.key() == Qt.Key_Home else self.count() if event.key() == Qt.Key_End else self.currentRow()
            row = start + direction
            while 0 <= row < self.count():
                item = self.item(row)
                if not item.isHidden() and isinstance(item.data(Qt.UserRole), int) and item.data(Qt.UserRole) >= 0:
                    self.setCurrentRow(row)
                    return
                row += direction
            return
        super().keyPressEvent(event)


class EnterpriseNavigationDelegate(QStyledItemDelegate):
    """Paint category separators and animated navigation states."""

    def paint(self, painter: QPainter, option, index):
        view = self.parent()
        if index.data(Qt.UserRole) == -1:
            painter.save()
            painter.setFont(QFont("Segoe UI", 8, QFont.DemiBold))
            painter.setPen(QColor("#B7C4CF"))
            title = str(index.data(Qt.DisplayRole) or "")
            rect = option.rect.adjusted(8, 5, -6, -2)
            painter.drawText(rect, Qt.AlignVCenter | Qt.AlignLeft, title)
            width = painter.fontMetrics().horizontalAdvance(title)
            left = rect.left() + width + 8
            if left < rect.right():
                painter.setPen(QPen(QColor("#263442"), 1))
                painter.drawLine(left, rect.center().y(), rect.right(), rect.center().y())
            painter.restore()
            return

        painter.save()
        row = index.row()
        progress = 0.0
        if row == getattr(view, "selected_row", -1):
            progress = getattr(view, "selection_progress", 1.0)
        elif row == getattr(view, "previous_row", -1):
            progress = 1.0 - getattr(view, "selection_progress", 1.0)
        hover = getattr(view, "hover_progress", 0.0) if row == getattr(view, "hover_row", -1) else 0.0
        rect = option.rect.adjusted(2, 1, -2, -1)
        if hover:
            painter.setBrush(QColor(48, 55, 68, int(150 * hover)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, 6, 6)
        if progress:
            painter.setBrush(QColor(23, 66, 47, int(255 * progress)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, 6, 6)
            painter.setBrush(QColor("#00C853"))
            painter.drawRoundedRect(rect.left(), rect.top(), 3, rect.height(), 2, 2)
        painter.restore()

        clean = QStyleOptionViewItem(option)
        clean.state &= ~QStyle.State_Selected
        clean.state &= ~QStyle.State_MouseOver
        super().paint(painter, clean, index)
