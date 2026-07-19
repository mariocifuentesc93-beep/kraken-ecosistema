from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
)


class CardWidget(QFrame):

    def __init__(
        self,
        title="",
        value="",
        parent=None,
    ):

        super().__init__(parent)

        self.setFrameShape(
            QFrame.StyledPanel
        )

        layout = QVBoxLayout(self)

        self.lblTitle = QLabel(title)

        self.lblTitle.setAlignment(
            Qt.AlignCenter
        )

        self.lblValue = QLabel(str(value))

        self.lblValue.setAlignment(
            Qt.AlignCenter
        )

        font = self.lblValue.font()

        font.setPointSize(18)

        font.setBold(True)

        self.lblValue.setFont(font)

        layout.addWidget(
            self.lblTitle
        )

        layout.addWidget(
            self.lblValue
        )

    # ----------------------------------------------

    def setTitle(self, title):

        self.lblTitle.setText(title)

    # ----------------------------------------------

    def setValue(self, value):

        self.lblValue.setText(str(value))