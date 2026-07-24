from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
)

from dashboard.widgets.status_badge import StatusBadge


class ConnectionIndicator(QWidget):

    testRequested = Signal()

    def __init__(self, title="", parent=None):

        super().__init__(parent)

        main = QHBoxLayout(self)

        main.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        left = QVBoxLayout()

        self.lblTitle = QLabel(title)

        font = self.lblTitle.font()

        font.setBold(True)

        self.lblTitle.setFont(font)

        self.lblSubtitle = QLabel("")

        left.addWidget(
            self.lblTitle
        )

        left.addWidget(
            self.lblSubtitle
        )

        main.addLayout(
            left,
            1,
        )

        self.badge = StatusBadge(
            "OFFLINE"
        )

        main.addWidget(
            self.badge
        )

        self.btnTest = QPushButton(
            "Probar"
        )

        self.btnTest.clicked.connect(
            self.testRequested.emit
        )

        main.addWidget(
            self.btnTest
        )

    # ------------------------------------------

    def setTitle(self, text):

        self.lblTitle.setText(text)

    # ------------------------------------------

    def setSubtitle(self, text):

        self.lblSubtitle.setText(text)

    # ------------------------------------------

    def setStatus(self, status):

        self.badge.setStatus(status)

    def setConnectionState(self, state):
        """Keep the visible status and action button synchronized."""
        normalized = str(state or "DISCONNECTED").strip().upper()
        labels = {
            "DISCONNECTED": ("Desconectado", "Conectar", True),
            "CONNECTING": ("Conectando", "Conectando...", False),
            "CONNECTED": ("Conectado", "Desconectar", True),
            "ERROR": ("Error", "Reintentar", True),
        }
        status, button, enabled = labels.get(
            normalized,
            labels["ERROR"],
        )
        self.badge.setStatus(status)
        self.btnTest.setText(button)
        self.btnTest.setEnabled(enabled)
