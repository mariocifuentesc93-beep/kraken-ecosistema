from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
)


class ChannelsPage(QWidget):

    def __init__(self):

        super().__init__()

        layout = QVBoxLayout(self)

        label = QLabel(
            "La administración de canales será migrada\n"
            "a la nueva arquitectura Profile → Telegram."
        )

        label.setWordWrap(True)

        layout.addWidget(label)

        layout.addStretch()