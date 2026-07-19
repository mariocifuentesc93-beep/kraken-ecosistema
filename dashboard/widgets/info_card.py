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
)


class InfoCard(QWidget):

    def __init__(
        self,
        title: str,
        message: str = "",
        parent=None,
    ):

        super().__init__(parent)

        self.card_title = title

        self.setMinimumSize(300, 120)

        self.setStyleSheet(card_style())

        self.build_ui(message)

    # ---------------------------------------------------------

    def build_ui(self, message):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(15, 15, 15, 15)

        layout.setSpacing(10)

        self.title = QLabel(self.card_title)

        self.title.setStyleSheet(title_style())

        self.message = QLabel(message)

        self.message.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.message.setWordWrap(True)

        self.message.setStyleSheet(subtitle_style())

        layout.addWidget(self.title)

        layout.addWidget(self.message)

        layout.addStretch()

    # ---------------------------------------------------------

    def set_title(self, title):

        self.card_title = title

        self.title.setText(title)

    # ---------------------------------------------------------

    def set_text(self, text):

        self.message.setText(str(text))

    # Compatibilidad con código anterior
    def set_message(self, text):

        self.set_text(text)

    # ---------------------------------------------------------

    def append(self, text):

        current = self.message.text()

        if current:

            current += "\n"

        current += str(text)

        self.message.setText(current)

    # ---------------------------------------------------------

    def prepend(self, text):

        current = self.message.text()

        if current:

            self.message.setText(f"{text}\n{current}")

        else:

            self.message.setText(str(text))

    # ---------------------------------------------------------

    def clear(self):

        self.message.clear()

    # ---------------------------------------------------------

    def get_text(self):

        return self.message.text()