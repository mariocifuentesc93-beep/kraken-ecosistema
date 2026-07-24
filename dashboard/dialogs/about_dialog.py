from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout
from dashboard.branding import application_icon, logo_pixmap

from version import (
    APPLICATION_NAME,
    DEVELOPMENT_STATUS,
    COPYRIGHT,
    RELEASE_CHANNEL,
    REPOSITORY_NAME,
    VERSION,
)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Acerca de Kraken Bot")
        self.setWindowIcon(application_icon())
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        logo = QLabel(); logo.setPixmap(logo_pixmap(82)); logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)
        title = QLabel(APPLICATION_NAME); title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        layout.addWidget(QLabel(f"Versión: {VERSION}"))
        layout.addWidget(QLabel(f"Repositorio: {REPOSITORY_NAME}"))
        layout.addWidget(QLabel(f"Canal: {RELEASE_CHANNEL}"))
        layout.addWidget(QLabel(f"Estado: {DEVELOPMENT_STATUS}"))
        copyright_label = QLabel(COPYRIGHT); copyright_label.setAlignment(Qt.AlignCenter); copyright_label.setStyleSheet("color:#B0BEC5;")
        layout.addWidget(copyright_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
