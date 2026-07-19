from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config.symbols import get_symbols
from dashboard.widgets.account_selector import AccountSelector
from dashboard.widgets.risk_widget import RiskWidget
from dashboard.widgets.section_widget import SectionWidget
from dashboard.widgets.statistics_panel import StatisticsPanel
from dashboard.widgets.symbol_selector import SymbolSelector
from dashboard.widgets.telegram_selector import TelegramSelector
from models.profile import Profile
from repositories.mt5_account_repository import mt5_account_repository
from repositories.profile_repository import profile_repository
from repositories.symbol_repository import symbol_repository
from repositories.telegram_account_repository import telegram_account_repository


class ProfileDialog(QDialog):
    """Repository-backed editor for a trading profile."""

    def __init__(self, profile=None, parent=None):
        super().__init__(parent)

        self.profile = profile
        self._profile_symbols = {}

        self.setWindowTitle("Perfil Kraken")
        self.resize(1200, 850)

        self.build_ui()
        self.load_repository_data()

        if profile is not None:
            self.load_profile(profile)

    def build_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.build_general_tab()
        self.build_trading_tab()
        self.build_risk_tab()
        self.build_mt5_tab()
        self.build_telegram_tab()
        self.build_symbols_tab()
        self.build_statistics_tab()
        self.build_audit_tab()

        buttons = QHBoxLayout()
        buttons.addStretch()

        self.btnDuplicate = QPushButton("Duplicar")
        self.btnExport = QPushButton("Exportar")
        self.btnImport = QPushButton("Importar")
        self.btnPreview = QPushButton("Vista previa")
        self.btnSave = QPushButton("Guardar")
        self.btnCancel = QPushButton("Cancelar")

        for button in (
            self.btnDuplicate,
            self.btnExport,
            self.btnImport,
            self.btnPreview,
            self.btnSave,
            self.btnCancel,
        ):
            buttons.addWidget(button)

        layout.addLayout(buttons)

        self.btnCancel.clicked.connect(self.reject)
        self.btnSave.clicked.connect(self.save_profile)

    def build_general_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        section = SectionWidget("Información General")
        form = QFormLayout()

        self.txtName = QLineEdit()
        self.txtDescription = QTextEdit()
        self.cboMode = QComboBox()
        self.cboMode.addItems(["OFF", "SIMULATION", "DEMO", "LIVE"])
        self.spnCapital = QDoubleSpinBox()
        self.spnCapital.setMaximum(999999999)
        self.spnMagic = QSpinBox()
        self.spnMagic.setMaximum(999999999)
        self.txtComment = QLineEdit()

        form.addRow("Nombre", self.txtName)
        form.addRow("Descripción", self.txtDescription)
        form.addRow("Modo", self.cboMode)
        form.addRow("Capital", self.spnCapital)
        form.addRow("Magic Number", self.spnMagic)
        form.addRow("Comentario", self.txtComment)

        section.addLayout(form)
        layout.addWidget(section)
        layout.addStretch()
        self.tabs.addTab(page, "General")

    def build_trading_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        section = SectionWidget("Trading")
        form = QFormLayout()

        self.cboExecution = QComboBox()
        self.cboExecution.addItems(["OFF", "SIMULATION", "DEMO", "LIVE"])
        self.cboRiskMode = QComboBox()
        self.cboRiskMode.addItems(["PERCENT", "AMOUNT", "LOT"])
        self.spnMaxTrades = QSpinBox()
        self.spnScore = QDoubleSpinBox()
        self.spnTP = QSpinBox()

        form.addRow("Modo", self.cboExecution)
        form.addRow("Riesgo", self.cboRiskMode)
        form.addRow("Máx. Operaciones", self.spnMaxTrades)
        form.addRow("Score mínimo", self.spnScore)
        form.addRow("TP Objetivo", self.spnTP)

        section.addLayout(form)
        layout.addWidget(section)
        layout.addStretch()
        self.tabs.addTab(page, "Trading")

    def build_risk_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.riskWidget = RiskWidget()
        layout.addWidget(self.riskWidget)
        layout.addStretch()
        self.tabs.addTab(page, "Riesgo")

        self.cboRiskMode.currentTextChanged.connect(self._set_risk_widget_mode)
        self.riskWidget.group.buttonClicked.connect(self._sync_risk_mode)

    def build_mt5_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        section = SectionWidget("Cuentas MT5")
        self.mt5Selector = AccountSelector()
        section.addWidget(self.mt5Selector)
        layout.addWidget(section)
        layout.addStretch()
        self.tabs.addTab(page, "MT5")

    def build_telegram_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        section = SectionWidget("Cuentas Telegram")
        self.telegramSelector = TelegramSelector()
        section.addWidget(self.telegramSelector)
        layout.addWidget(section)
        layout.addStretch()
        self.tabs.addTab(page, "Telegram")

    def build_symbols_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        section = SectionWidget("Símbolos habilitados")
        self.symbolSelector = SymbolSelector()
        section.addWidget(self.symbolSelector)
        layout.addWidget(section)
        layout.addStretch()
        self.tabs.addTab(page, "Símbolos")

    def build_statistics_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.statisticsPanel = StatisticsPanel()
        layout.addWidget(self.statisticsPanel)
        layout.addStretch()
        self.tabs.addTab(page, "Estadísticas")

    def build_audit_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        section = SectionWidget("Auditoría")
        form = QFormLayout()

        self.lblCreated = QLabel("-")
        self.lblUpdated = QLabel("-")
        self.lblOperations = QLabel("0")
        self.lblProfit = QLabel("0")
        self.lblWinRate = QLabel("0 %")

        form.addRow("Creado", self.lblCreated)
        form.addRow("Actualizado", self.lblUpdated)
        form.addRow("Operaciones", self.lblOperations)
        form.addRow("Profit", self.lblProfit)
        form.addRow("Win Rate", self.lblWinRate)

        section.addLayout(form)
        layout.addWidget(section)
        layout.addStretch()
        self.tabs.addTab(page, "Auditoría")

    def load_repository_data(self):
        """Populate selectors from their repository-backed sources."""
        self.set_mt5_accounts(mt5_account_repository.get_all())
        self.set_telegram_accounts(telegram_account_repository.get_all())
        self.set_symbols(get_symbols())

    def load_profile(self, profile=None):
        if profile is not None:
            self.profile = profile

        if self.profile is None:
            return

        profile = self.profile
        self.txtName.setText(profile.name)
        self.txtDescription.setPlainText(profile.description)
        self.txtComment.setText(profile.comment)
        self.spnMagic.setValue(profile.magic_number)
        self.cboMode.setCurrentText(profile.operation_mode)
        self.cboExecution.setCurrentText(profile.execution_mode)
        self.cboRiskMode.setCurrentText(profile.risk_mode)
        self.spnMaxTrades.setValue(profile.max_open_trades)
        self.spnTP.setValue(profile.tp_level)

        self._set_risk_widget_mode(profile.risk_mode)
        if profile.risk_mode == "PERCENT":
            self.riskWidget.value.setValue(profile.risk_percent)
        elif profile.risk_mode == "AMOUNT":
            self.riskWidget.value.setValue(profile.risk_amount)
        else:
            self.riskWidget.value.setValue(profile.fixed_lot)

        self.mt5Selector.setSelected(self._as_id_list(profile.default_mt5_account))
        self.telegramSelector.setSelected(
            self._as_id_list(profile.telegram_account_id)
        )

        self._profile_symbols = {
            symbol.symbol: symbol
            for symbol in symbol_repository.get_all(profile.id)
        }
        available_symbols = list(dict.fromkeys([
            *get_symbols(),
            *self._profile_symbols.keys(),
        ]))
        self.set_symbols(available_symbols)
        self.symbolSelector.setSelected([
            symbol.symbol
            for symbol in self._profile_symbols.values()
            if symbol.enabled
        ])

        self.set_audit_data({
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
            "operations": profile.total_operations,
            "profit": profile.net_profit,
            "win_rate": profile.win_rate,
        })

    def get_profile_data(self):
        risk_mode = self._risk_mode()
        risk_value = self.riskWidget.value.value()

        return {
            "name": self.txtName.text().strip(),
            "description": self.txtDescription.toPlainText(),
            "comment": self.txtComment.text(),
            "operation_mode": self.cboMode.currentText(),
            "magic_number": self.spnMagic.value(),
            "execution_mode": self.cboExecution.currentText(),
            "risk_mode": risk_mode,
            "risk_percent": risk_value if risk_mode == "PERCENT" else 0.0,
            "risk_amount": risk_value if risk_mode == "AMOUNT" else 0.0,
            "fixed_lot": risk_value if risk_mode == "LOT" else 0.0,
            "max_open_trades": self.spnMaxTrades.value(),
            "tp_level": self.spnTP.value(),
            "default_mt5_account": self._selected_account_id(self.mt5Selector),
            "telegram_account_id": self._selected_account_id(
                self.telegramSelector
            ),
        }

    def set_mt5_accounts(self, accounts):
        self.mt5Selector.loadAccounts(accounts)

    def set_telegram_accounts(self, accounts):
        self.telegramSelector.loadAccounts(accounts)

    def set_symbols(self, symbols):
        self.symbolSelector.loadSymbols([
            getattr(symbol, "symbol", symbol)
            for symbol in symbols
        ])

    def set_statistics(self, stats):
        if not stats:
            self.statisticsPanel.clear()
            return

        for key, value in stats.items():
            self.statisticsPanel.setValue(key, value)

    def set_audit_data(self, audit):
        if not audit:
            return

        self.lblCreated.setText(str(audit.get("created_at") or "-"))
        self.lblUpdated.setText(str(audit.get("updated_at") or "-"))
        self.lblOperations.setText(str(audit.get("operations", 0)))
        self.lblProfit.setText(str(audit.get("profit", 0)))
        self.lblWinRate.setText(f'{audit.get("win_rate", 0)} %')

    def save_profile(self):
        data = self.get_profile_data()
        if not data["name"]:
            QMessageBox.warning(self, "Perfil", "Debe ingresar un nombre.")
            return

        profile = self.profile or Profile()
        for field, value in data.items():
            setattr(profile, field, value)

        profile.active = True
        profile.enabled = True

        try:
            if profile.id is None:
                profile_repository.create(profile)
            else:
                profile_repository.update(profile)
            self._save_symbols(profile.id)
        except Exception as error:
            QMessageBox.critical(
                self,
                "Perfil",
                f"No se pudo guardar el perfil:\n{error}",
            )
            return

        self.profile = profile
        self.accept()

    def _save_symbols(self, profile_id):
        selected = set(self.symbolSelector.selectedSymbols())

        for name, symbol in self._profile_symbols.items():
            symbol.enabled = name in selected
            symbol_repository.update(
                symbol.id,
                symbol.enabled,
                symbol.mt5_symbol,
                symbol.description,
                symbol.aliases,
                symbol.risk,
                symbol.min_lot,
                symbol.max_lot,
                symbol.action,
            )

        for name in selected - self._profile_symbols.keys():
            symbol_repository.create(
                profile_id,
                True,
                name,
                name,
                "",
                "",
                1.0,
                0.01,
                100.0,
                "trade",
            )

    def _set_risk_widget_mode(self, mode):
        buttons = {
            "PERCENT": self.riskWidget.percent,
            "AMOUNT": self.riskWidget.amount,
            "LOT": self.riskWidget.lot,
        }
        button = buttons.get(mode, self.riskWidget.percent)
        button.setChecked(True)

    def _sync_risk_mode(self, *_):
        self.cboRiskMode.setCurrentText(self._risk_mode())

    def _risk_mode(self):
        if self.riskWidget.amount.isChecked():
            return "AMOUNT"
        if self.riskWidget.lot.isChecked():
            return "LOT"
        return "PERCENT"

    @staticmethod
    def _as_id_list(value):
        return [] if value is None else [value]

    @staticmethod
    def _selected_account_id(selector):
        accounts = selector.selectedAccounts()
        if not accounts:
            return None

        account = accounts[0]
        if isinstance(account, dict):
            return account.get("id")
        return getattr(account, "id", None)
