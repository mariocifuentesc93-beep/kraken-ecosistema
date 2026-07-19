from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QRadioButton,
    QDoubleSpinBox,
    QCheckBox,
    QLabel,
    QButtonGroup,
)


class RiskWidget(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        layout = QVBoxLayout(self)

        modes = QHBoxLayout()

        self.group = QButtonGroup(self)

        self.percent = QRadioButton("%")

        self.amount = QRadioButton("$")

        self.lot = QRadioButton("LOT")

        self.group.addButton(self.percent)

        self.group.addButton(self.amount)

        self.group.addButton(self.lot)

        self.percent.setChecked(True)

        modes.addWidget(self.percent)

        modes.addWidget(self.amount)

        modes.addWidget(self.lot)

        layout.addLayout(modes)

        layout.addWidget(
            QLabel("Valor")
        )

        self.value = QDoubleSpinBox()

        self.value.setDecimals(2)

        self.value.setMaximum(
            99999999
        )

        layout.addWidget(
            self.value
        )

        self.breakEven = QCheckBox(
            "Break Even"
        )

        self.trailing = QCheckBox(
            "Trailing Stop"
        )

        self.partial = QCheckBox(
            "Take Profit Parcial"
        )

        self.daily = QCheckBox(
            "Límite Diario"
        )

        self.drawdown = QCheckBox(
            "Control Drawdown"
        )

        layout.addWidget(
            self.breakEven
        )

        layout.addWidget(
            self.trailing
        )

        layout.addWidget(
            self.partial
        )

        layout.addWidget(
            self.daily
        )

        layout.addWidget(
            self.drawdown
        )