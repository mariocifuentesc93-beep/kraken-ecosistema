from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
)


class SearchWidget(QWidget):

    searchChanged = Signal(str)

    def __init__(self, parent=None):

        super().__init__(parent)

        layout = QHBoxLayout(self)

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.edit = QLineEdit()

        self.edit.setPlaceholderText(
            "Buscar..."
        )

        self.button = QPushButton("🔍")

        self.button.setFixedWidth(40)

        layout.addWidget(
            self.edit
        )

        layout.addWidget(
            self.button
        )

        self.edit.textChanged.connect(
            self.searchChanged.emit
        )