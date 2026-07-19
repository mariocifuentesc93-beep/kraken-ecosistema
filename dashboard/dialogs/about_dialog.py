from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from version import (
    APPLICATION_NAME,
    DEVELOPMENT_STATUS,
    REPOSITORY_NAME,
    VERSION,
)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Acerca de Kraken Bot")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        title = QLabel(APPLICATION_NAME)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        layout.addWidget(QLabel(f"Versión: {VERSION}"))
        layout.addWidget(QLabel(f"Repositorio: {REPOSITORY_NAME}"))
        layout.addWidget(QLabel(f"Estado: {DEVELOPMENT_STATUS}"))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
