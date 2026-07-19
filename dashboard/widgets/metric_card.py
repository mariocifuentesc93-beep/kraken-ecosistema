from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
)

from dashboard.styles import (
    card_style,
    title_style,
    subtitle_style,
    value_style,
)


class MetricCard(QWidget):

    def __init__(
        self,
        title,
        value="0",
        subtitle="",
        icon="📊",
        parent=None,
    ):

        super().__init__(parent)

        self.icon = icon

        self.card_title = title

        self.setMinimumSize(230, 130)

        self.setStyleSheet(card_style())

        self.build_ui(value, subtitle)

    # ---------------------------------------------------------

    def build_ui(self, value, subtitle):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(15, 15, 15, 15)

        layout.setSpacing(8)

        self.title = QLabel()

        self.title.setStyleSheet(title_style())

        self.title.setText(f"{self.icon}  {self.card_title}")

        self.value = QLabel(str(value))

        self.value.setAlignment(Qt.AlignCenter)

        self.value.setStyleSheet(value_style())

        self.subtitle = QLabel(subtitle)

        self.subtitle.setAlignment(Qt.AlignCenter)

        self.subtitle.setStyleSheet(subtitle_style())

        layout.addWidget(self.title)

        layout.addStretch()

        layout.addWidget(self.value)

        layout.addWidget(self.subtitle)

    # ---------------------------------------------------------

    def set_title(self, text):

        self.card_title = text

        self.title.setText(f"{self.icon}  {text}")

    # ---------------------------------------------------------

    def set_icon(self, icon):

        self.icon = icon

        self.title.setText(f"{self.icon}  {self.card_title}")

    # ---------------------------------------------------------

    def set_value(self, value):

        self.value.setText(str(value))

    # ---------------------------------------------------------

    def set_subtitle(self, text):

        self.subtitle.setText(str(text))

    # ---------------------------------------------------------

    def update_data(

        self,

        value=None,

        subtitle=None,

    ):

        if value is not None:

            self.set_value(value)

        if subtitle is not None:

            self.set_subtitle(subtitle)