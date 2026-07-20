"""Central responsive form contract for Kraken Enterprise pages."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
)

from dashboard.ui_theme import refresh_widget_style


class ProfessionalFormManager:
    """Apply one form rhythm and semantic region model to existing pages."""

    REGIONS = ("sectionTitle", "description", "toolbar", "filters", "content", "actions")
    SPACING = 8
    FIELD_MINIMUM_WIDTH = 80
    BUTTON_HEIGHT = 30
    _FIELDS = (QComboBox, QDateEdit, QDoubleSpinBox, QLineEdit, QSpinBox)

    def configure(self, page):
        page.setProperty("professionalForm", True)
        page.setProperty("formRegions", list(self.REGIONS))
        root = page.layout()
        if root is not None:
            self._normalize_layout(root)
        self._configure_fields(page)
        self._configure_buttons(page)
        refresh_widget_style(page)
        return page

    def _normalize_layout(self, layout):
        layout.setSpacing(self.SPACING)
        if isinstance(layout, QGridLayout):
            layout.setHorizontalSpacing(self.SPACING)
            layout.setVerticalSpacing(self.SPACING)
            layout.setColumnStretch(1, 1)
            self._align_grid_labels(layout)
        elif isinstance(layout, QHBoxLayout):
            self._align_horizontal_labels(layout)
        for index in range(layout.count()):
            item = layout.itemAt(index)
            child = item.layout()
            if child is not None:
                child.setContentsMargins(0, 0, 0, 0)
                self._normalize_layout(child)

    def _align_grid_labels(self, layout):
        for index in range(layout.count()):
            row, column, _, _ = layout.getItemPosition(index)
            widget = layout.itemAt(index).widget()
            if isinstance(widget, QLabel):
                below = layout.itemAtPosition(row + 1, column)
                right = layout.itemAtPosition(row, column + 1)
                if below is not None and isinstance(below.widget(), self._FIELDS):
                    widget.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
                elif right is not None and isinstance(right.widget(), self._FIELDS):
                    widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                widget.setProperty("formRegion", "filters")
            elif column > 0 and widget is not None:
                widget.setProperty("formRegion", "content")

    def _align_horizontal_labels(self, layout):
        for index in range(layout.count() - 1):
            label = layout.itemAt(index).widget()
            field = layout.itemAt(index + 1).widget()
            if isinstance(label, QLabel) and isinstance(field, self._FIELDS):
                label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                label.setProperty("formRegion", "filters")

    def _configure_fields(self, page):
        for field_type in self._FIELDS:
            for field in page.findChildren(field_type):
                field.setMinimumWidth(self.FIELD_MINIMUM_WIDTH)
                field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                field.setProperty("formRegion", "filters")
                refresh_widget_style(field)

    def _configure_buttons(self, page):
        action_words = ("guardar", "eliminar", "reiniciar", "activar", "desactivar", "crear")
        danger_words = ("eliminar", "reiniciar", "desactivar")
        success_words = ("guardar", "activar", "crear", "nuevo", "nueva")
        for button in page.findChildren(QPushButton):
            text = button.text().lower()
            button.setMinimumHeight(self.BUTTON_HEIGHT)
            button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            button.setProperty(
                "formRegion",
                "actions" if any(word in text for word in action_words) else "toolbar",
            )
            if any(word in text for word in danger_words):
                button.setProperty("variant", "danger")
            elif any(word in text for word in success_words):
                button.setProperty("variant", "success")
            refresh_widget_style(button)


professional_forms = ProfessionalFormManager()
