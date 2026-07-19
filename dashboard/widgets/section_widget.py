from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QFrame,
    QSizePolicy,
)


class SectionWidget(QFrame):
    """
    Contenedor reutilizable para agrupar información.

    Ejemplo:

    ┌──────────────────────────────────────────────┐
    │ GENERAL                                      │
    ├──────────────────────────────────────────────┤
    │                                              │
    │ contenido                                    │
    │                                              │
    └──────────────────────────────────────────────┘
    """

    def __init__(self, title="", parent=None):

        super().__init__(parent)

        self.setObjectName("SectionWidget")

        self.setFrameShape(QFrame.StyledPanel)

        self.setFrameShadow(QFrame.Raised)

        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Maximum,
        )

        self.main_layout = QVBoxLayout(self)

        self.main_layout.setContentsMargins(
            15,
            15,
            15,
            15,
        )

        self.main_layout.setSpacing(12)

        self.title = QLabel(title)

        self.title.setAlignment(
            Qt.AlignLeft | Qt.AlignVCenter
        )

        self.title.setObjectName(
            "SectionTitle"
        )

        self.separator = QFrame()

        self.separator.setFrameShape(
            QFrame.HLine
        )

        self.separator.setFrameShadow(
            QFrame.Sunken
        )

        self.body = QVBoxLayout()

        self.body.setSpacing(10)

        self.main_layout.addWidget(
            self.title
        )

        self.main_layout.addWidget(
            self.separator
        )

        self.main_layout.addLayout(
            self.body
        )

    # -------------------------------------------------

    def addWidget(self, widget):

        self.body.addWidget(widget)

    # -------------------------------------------------

    def addLayout(self, layout):

        self.body.addLayout(layout)

    # -------------------------------------------------

    def setTitle(self, text):

        self.title.setText(text)