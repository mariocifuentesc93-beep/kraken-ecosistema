from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QPushButton,
    QLabel,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
)

from dashboard.widgets.section_widget import SectionWidget
from dashboard.widgets.risk_widget import RiskWidget
from dashboard.widgets.statistics_panel import StatisticsPanel


class SymbolDialog(QDialog):

    def __init__(self, symbol=None, parent=None):

        super().__init__(parent)

        self.symbol = symbol

        self.setWindowTitle("Configuración del Símbolo")

        self.resize(1100, 800)

        self.build_ui()

    # ------------------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()

        layout.addWidget(self.tabs)

        self.build_general_tab()

        self.build_trading_tab()

        self.build_risk_tab()

        self.build_filters_tab()

        self.build_statistics_tab()

        buttons = QHBoxLayout()

        buttons.addStretch()

        self.btnSave = QPushButton("Guardar")

        self.btnCancel = QPushButton("Cancelar")

        buttons.addWidget(self.btnSave)

        buttons.addWidget(self.btnCancel)

        layout.addLayout(buttons)

        self.btnSave.clicked.connect(self.accept)

        self.btnCancel.clicked.connect(self.reject)

    # ------------------------------------------------------------

    def build_general_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget("Información")

        form = QFormLayout()

        self.txtName = QLineEdit()

        self.txtMt5 = QLineEdit()

        self.cboGroup = QComboBox()

        self.cboGroup.addItems([
            "EMAS",
            "LION"
        ])

        self.chkEnabled = QCheckBox(
            "Símbolo habilitado"
        )

        form.addRow(
            "Nombre",
            self.txtName
        )

        form.addRow(
            "Símbolo MT5",
            self.txtMt5
        )

        form.addRow(
            "Grupo",
            self.cboGroup
        )

        form.addRow(
            "",
            self.chkEnabled
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(page, "General")

    # ------------------------------------------------------------

    def build_trading_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget("Trading")

        form = QFormLayout()

        self.cboExecution = QComboBox()

        self.cboExecution.addItems([
            "OFF",
            "SIMULATION",
            "DEMO",
            "LIVE"
        ])

        self.spnPriority = QSpinBox()

        self.spnPriority.setRange(1, 100)

        self.spnTP = QSpinBox()

        self.spnTP.setRange(1, 10)

        self.spnMaxTrades = QSpinBox()

        self.spnMaxTrades.setRange(1, 100)

        form.addRow(
            "Modo",
            self.cboExecution
        )

        form.addRow(
            "Prioridad",
            self.spnPriority
        )

        form.addRow(
            "TP",
            self.spnTP
        )

        form.addRow(
            "Máx. operaciones",
            self.spnMaxTrades
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(page, "Trading")

    # ------------------------------------------------------------

    def build_risk_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        self.riskWidget = RiskWidget()

        layout.addWidget(self.riskWidget)

        layout.addStretch()

        self.tabs.addTab(page, "Riesgo")

    # ------------------------------------------------------------

    def build_filters_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget("Filtros")

        form = QFormLayout()

        self.chkSpread = QCheckBox(
            "Control de spread"
        )

        self.spnSpread = QDoubleSpinBox()

        self.spnSpread.setMaximum(1000)

        self.chkHours = QCheckBox(
            "Horario permitido"
        )

        self.txtStart = QLineEdit("00:00")

        self.txtEnd = QLineEdit("23:59")

        self.chkVolatility = QCheckBox(
            "Filtro volatilidad"
        )

        form.addRow(
            "",
            self.chkSpread
        )

        form.addRow(
            "Spread máximo",
            self.spnSpread
        )

        form.addRow(
            "",
            self.chkHours
        )

        form.addRow(
            "Desde",
            self.txtStart
        )

        form.addRow(
            "Hasta",
            self.txtEnd
        )

        form.addRow(
            "",
            self.chkVolatility
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(page, "Filtros")

    # ------------------------------------------------------------

    def build_statistics_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        self.statistics = StatisticsPanel()

        layout.addWidget(self.statistics)

        layout.addStretch()

        self.tabs.addTab(page, "Estadísticas")

    def load_symbol(self, symbol):

        if symbol is None:

            return

        self.symbol = symbol

        self.txtName.setText(
            getattr(symbol, "name", "")
        )

        self.txtMt5.setText(
            getattr(symbol, "mt5_symbol", "")
        )

        self.cboGroup.setCurrentText(
            getattr(symbol, "group", "EMAS")
        )

        self.chkEnabled.setChecked(
            getattr(symbol, "enabled", True)
        )

        self.cboExecution.setCurrentText(
            getattr(symbol, "execution_mode", "LIVE")
        )

        self.spnPriority.setValue(
            getattr(symbol, "priority", 1)
        )

        self.spnTP.setValue(
            getattr(symbol, "tp_level", 1)
        )

        self.spnMaxTrades.setValue(
            getattr(symbol, "max_trades", 1)
        )

    def get_symbol_data(self):

        return {

            "name": self.txtName.text(),

            "mt5_symbol": self.txtMt5.text(),

            "group": self.cboGroup.currentText(),

            "enabled": self.chkEnabled.isChecked(),

            "execution_mode": self.cboExecution.currentText(),

            "priority": self.spnPriority.value(),

            "tp_level": self.spnTP.value(),

            "max_trades": self.spnMaxTrades.value(),

            "risk": {

                "value": self.riskWidget.value.value(),

                "percent": self.riskWidget.percent.isChecked(),

                "amount": self.riskWidget.amount.isChecked(),

                "lot": self.riskWidget.lot.isChecked(),

                "break_even": self.riskWidget.breakEven.isChecked(),

                "trailing": self.riskWidget.trailing.isChecked(),

                "partial_tp": self.riskWidget.partial.isChecked(),

                "daily_limit": self.riskWidget.daily.isChecked(),

                "drawdown": self.riskWidget.drawdown.isChecked(),

            },

            "filters": {

                "spread_enabled": self.chkSpread.isChecked(),

                "max_spread": self.spnSpread.value(),

                "hours_enabled": self.chkHours.isChecked(),

                "start_time": self.txtStart.text(),

                "end_time": self.txtEnd.text(),

                "volatility_filter": self.chkVolatility.isChecked(),

            }

        }

