from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QDoubleSpinBox,
    QComboBox,
    QCheckBox,
    QPushButton,
    QHBoxLayout,
)


class SymbolDialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Símbolo")

        self.resize(500,420)

        self.build_ui()

    # ---------------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.enabled = QCheckBox()

        self.enabled.setChecked(True)

        self.symbol = QLineEdit()

        self.description = QLineEdit()

        self.aliases = QLineEdit()

        self.risk = QDoubleSpinBox()

        self.risk.setDecimals(2)

        self.risk.setRange(0.01,100)

        self.risk.setValue(1)

        self.risk.setSuffix(" %")

        self.min_lot = QDoubleSpinBox()

        self.min_lot.setDecimals(2)

        self.min_lot.setRange(0.01,1000)

        self.min_lot.setValue(0.01)

        self.max_lot = QDoubleSpinBox()

        self.max_lot.setDecimals(2)

        self.max_lot.setRange(0.01,1000)

        self.max_lot.setValue(100)

        self.action = QComboBox()

        self.action.addItems(

            [

                "trade",

                "ignore",

                "ask",

            ]

        )

        form.addRow("Activo", self.enabled)

        form.addRow("Símbolo", self.symbol)

        form.addRow("Descripción", self.description)

        form.addRow("Alias", self.aliases)

        form.addRow("Riesgo", self.risk)

        form.addRow("Lote mínimo", self.min_lot)

        form.addRow("Lote máximo", self.max_lot)

        form.addRow("Acción", self.action)

        layout.addLayout(form)

        buttons = QHBoxLayout()

        buttons.addStretch()

        save = QPushButton("Guardar")

        cancel = QPushButton("Cancelar")

        save.clicked.connect(self.accept)

        cancel.clicked.connect(self.reject)

        buttons.addWidget(save)

        buttons.addWidget(cancel)

        layout.addLayout(buttons)

    # ---------------------------------------------------------

    def get_data(self):

        return {

            "enabled": self.enabled.isChecked(),

            "symbol": self.symbol.text().strip(),

            "description": self.description.text().strip(),

            "aliases": self.aliases.text().strip(),

            "risk": self.risk.value(),

            "min_lot": self.min_lot.value(),

            "max_lot": self.max_lot.value(),

            "action": self.action.currentText(),

        }