from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
)

from dashboard.styles import (
    card_style,
    title_style,
    subtitle_style,
    SUCCESS_COLOR,
    WARNING_COLOR,
    ERROR_COLOR,
)


class StatusCard(QWidget):

    COLORS = {
        "online": SUCCESS_COLOR,
        "warning": WARNING_COLOR,
        "offline": ERROR_COLOR,
    }

    TEXTS = {
        "online": "● En línea",
        "warning": "● Advertencia",
        "offline": "● Desconectado",
    }

    def __init__(
        self,
        title: str,
        status: str = "offline",
        parent=None,
    ):

        super().__init__(parent)

        self.title_text = title

        self.current_status = status

        self.setMinimumSize(220, 90)

        self.setStyleSheet(card_style())

        self.build_ui()

        self.set_status(status)

    # ---------------------------------------------------------

    def build_ui(self):

        layout = QHBoxLayout(self)

        layout.setContentsMargins(15, 15, 15, 15)

        left = QVBoxLayout()

        self.title = QLabel(self.title_text)

        self.title.setStyleSheet(title_style())

        self.status = QLabel()

        left.addWidget(self.title)

        left.addStretch()

        left.addWidget(self.status)

        layout.addLayout(left)

        self.indicator = QLabel("●")

        self.indicator.setAlignment(Qt.AlignCenter)

        self.indicator.setStyleSheet("""
            font-size:30px;
            font-weight:bold;
        """)

        layout.addWidget(self.indicator)

    # ---------------------------------------------------------

    def set_title(self, title):

        self.title_text = title

        self.title.setText(title)

    # ---------------------------------------------------------

    def set_status(self, status):

        self.current_status = status

        color = self.COLORS.get(status, ERROR_COLOR)

        text = self.TEXTS.get(status, "● Desconocido")

        self.indicator.setStyleSheet(f"""
            color:{color};
            font-size:30px;
            font-weight:bold;
        """)

        self.status.setStyleSheet(

            subtitle_style() + f"color:{color};"

        )

        self.status.setText(text)

    # ---------------------------------------------------------

    def get_status(self):

        return self.current_status

    # ---------------------------------------------------------

    def is_online(self):

        return self.current_status == "online"