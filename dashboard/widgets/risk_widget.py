from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QRadioButton,
    QDoubleSpinBox,
    QCheckBox,
    QLabel,
    QButtonGroup,
    QComboBox,
)


class RiskWidget(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        layout = QVBoxLayout(self)

        modes = QHBoxLayout()

        self.group = QButtonGroup(self)

        self.enabled = QCheckBox("Gestión de riesgo habilitada")
        self.enabled.setChecked(True)
        layout.addWidget(self.enabled)

        self.percent = QRadioButton("%")

        self.amount = QRadioButton("$")

        self.lot = QRadioButton("Lote fijo")

        self.group.addButton(self.percent)

        self.group.addButton(self.amount)
        self.group.addButton(self.lot)

        self.percent.setChecked(True)

        modes.addWidget(self.percent)

        modes.addWidget(self.amount)
        modes.addWidget(self.lot)

        layout.addLayout(modes)

        self.valueLabel = QLabel("Riesgo por operación (%)")
        layout.addWidget(self.valueLabel)

        self.value = QDoubleSpinBox()

        self.value.setDecimals(2)

        self.value.setMaximum(
            99999999
        )

        layout.addWidget(
            self.value
        )

        self.maxRiskPercent = QDoubleSpinBox()
        self.maxRiskPercent.setDecimals(2)
        self.maxRiskPercent.setRange(0.01, 10.0)
        self.maxRiskPercent.setValue(5.0)
        self.maxRiskPercent.setSuffix(" %")
        self.maxRiskPercent.setToolTip(
            "Límite máximo permitido para cualquier operación del perfil."
        )
        layout.addWidget(QLabel("Riesgo máximo permitido"))
        layout.addWidget(self.maxRiskPercent)

        self.group.buttonClicked.connect(self._update_value_presentation)

        self.breakEven = QCheckBox(
            "Break Even"
        )

        self.trailing = QCheckBox(
            "Trailing Stop"
        )

        self.partial = QCheckBox(
            "Take Profit Parcial"
        )

        self.tp1Management = QComboBox()
        self.tp1Management.addItem(
            "Proteger TP1: mover SL a TP1 sin cerrar volumen",
            "PROTECT_TP1",
        )
        self.tp1Management.addItem(
            "Cierre parcial: realizar una parte del volumen en TP1",
            "PARTIAL_CLOSE",
        )
        self.tp1Management.setToolTip(
            "Define qué ocurre al llegar a TP1. Proteger TP1 conserva la posición "
            "para buscar TP2 o TP3 y asegura la ganancia si el precio retrocede."
        )

        self.daily = QCheckBox(
            "Límite Diario"
        )

        self.drawdown = QCheckBox(
            "Control Drawdown"
        )

        self.drawdownLimit = QDoubleSpinBox()
        self.drawdownLimit.setDecimals(2)
        self.drawdownLimit.setRange(0.0, 100.0)
        self.drawdownLimit.setSuffix(" %")
        self.drawdownLimit.setToolTip(
            "Porcentaje máximo de drawdown permitido para este perfil. "
            "Al alcanzarlo, Kraken rechazará nuevas operaciones del perfil."
        )

        self.dailyLossLimit = QDoubleSpinBox()
        self.dailyLossLimit.setDecimals(2)
        self.dailyLossLimit.setRange(0.0, 99999999.0)
        self.dailyLossLimit.setPrefix("$ ")
        self.dailyLossLimit.setToolTip(
            "Pérdida acumulada máxima por día para este perfil. "
            "Al alcanzarla, no se aceptarán nuevas operaciones."
        )

        self.dailyProfitLimit = QDoubleSpinBox()
        self.dailyProfitLimit.setDecimals(2)
        self.dailyProfitLimit.setRange(0.0, 99999999.0)
        self.dailyProfitLimit.setPrefix("$ ")
        self.dailyProfitLimit.setToolTip(
            "Ganancia acumulada máxima por día. Es opcional; 0 la desactiva."
        )

        layout.addWidget(
            self.breakEven
        )

        layout.addWidget(
            self.trailing
        )

        layout.addWidget(QLabel("Acción al alcanzar TP1"))
        layout.addWidget(self.tp1Management)

        layout.addWidget(
            self.daily
        )

        layout.addWidget(QLabel("Pérdida diaria máxima"))
        layout.addWidget(self.dailyLossLimit)
        layout.addWidget(QLabel("Ganancia diaria máxima (opcional)"))
        layout.addWidget(self.dailyProfitLimit)

        layout.addWidget(
            self.drawdown
        )

        layout.addWidget(QLabel("Drawdown máximo"))
        layout.addWidget(self.drawdownLimit)

        self.daily.toggled.connect(self._set_daily_limits_enabled)
        self.drawdown.toggled.connect(self.drawdownLimit.setEnabled)
        self._set_daily_limits_enabled(False)
        self.drawdownLimit.setEnabled(False)
        self._update_value_presentation()
        self.value.setValue(2.0)

    def _set_daily_limits_enabled(self, enabled):
        self.dailyLossLimit.setEnabled(enabled)
        self.dailyProfitLimit.setEnabled(enabled)

    def _update_value_presentation(self, *_):
        self.value.setPrefix("")
        self.value.setSuffix("")
        self.value.setDecimals(2)
        if self.lot.isChecked():
            self.valueLabel.setText("Lote fijo")
            self.value.setRange(0.0, 100000.0)
            self.value.setToolTip("Volumen fijo solicitado para cada operación.")
        elif self.amount.isChecked():
            self.valueLabel.setText("Riesgo fijo por operación (USD)")
            self.value.setPrefix("$ ")
            self.value.setRange(0.0, 99999999.0)
            self.value.setToolTip(
                "Monto máximo que este perfil arriesgará por cada operación."
            )
        else:
            self.valueLabel.setText("Riesgo por operación (%)")
            self.value.setSuffix(" %")
            self.value.setRange(0.0, 100.0)
            self.value.setToolTip(
                "Porcentaje del capital de la cuenta que se arriesga por operación."
            )
