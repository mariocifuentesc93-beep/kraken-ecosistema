from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel


class StatusBadge(QLabel):

    COLORS = {
        "ONLINE": "#27AE60",
        "OFFLINE": "#E74C3C",
        "SIMULATION": "#F39C12",
        "DEMO": "#3498DB",
        "LIVE": "#27AE60",
        "WARNING": "#F1C40F",
        "ERROR": "#E74C3C",
        "INFO": "#5DADE2",
    }

    def __init__(self, text="", parent=None):

        super().__init__(parent)

        self.setAlignment(Qt.AlignCenter)

        self.setMinimumHeight(28)

        self.setStatus(text)

    # -------------------------------------------------

    def setStatus(self, status):

        status = status.upper()

        color = self.COLORS.get(
            status,
            "#7F8C8D"
        )

        self.setText(status)

        self.setStyleSheet(f"""
            QLabel {{
                background:{color};
                color:white;
                border-radius:6px;
                padding:4px 10px;
                font-weight:bold;
            }}
        """)
