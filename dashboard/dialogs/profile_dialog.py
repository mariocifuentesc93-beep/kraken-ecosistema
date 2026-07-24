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
from dashboard.dialogs.dialog_layout import fit_dialog_to_screen
from models.profile import Profile
from repositories.mt5_account_repository import mt5_account_repository
from repositories.profile_repository import profile_repository
from repositories.symbol_repository import symbol_repository
from repositories.telegram_account_repository import telegram_account_repository
from repositories.profile_telegram_repository import profile_telegram_channel_repository


class ProfileDialog(QDialog):
    """Repository-backed editor for a trading profile."""

    def __init__(self, profile=None, parent=None):
        super().__init__(parent)

        self.profile = profile
        self._profile_symbols = {}

        self.setWindowTitle("Perfil Kraken")
        fit_dialog_to_screen(self, 1200, 700)

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
        self.cboMode = QComboBox()
        self.cboMode.addItems(["OFF", "SIMULATION", "DEMO", "LIVE"])
        self.spnMagic = QSpinBox()
        self.spnMagic.setMaximum(999999999)
        self.txtComment = QLineEdit()

        form.addRow("Nombre", self.txtName)
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
        self.cboExecution.setToolTip(
            "Define el modo de ejecuci\u00f3n de este perfil. "
            "Este es el \u00fanico modo configurable del perfil."
        )
        # operation_mode remains a legacy persisted field.  Keep it synchronized
        # without presenting a second, conflicting selector to the operator.
        self.cboExecution.currentTextChanged.connect(self.cboMode.setCurrentText)
        self.cboRiskMode = QComboBox()
        self.cboRiskMode.addItems(["PERCENT", "AMOUNT"])
        self.spnMaxTrades = QSpinBox()
        self.spnMaxTrades.setToolTip(
            "Máximo de operaciones abiertas al mismo tiempo para este perfil. "
            "No limita la cantidad de operaciones cerradas durante el día."
        )
        self.spnScore = QDoubleSpinBox()
        self.spnScore.setRange(0.0, 100.0)
        self.spnScore.setDecimals(0)
        self.spnScore.setSuffix(" / 100")
        self.spnScore.setToolTip(
            "Puntaje mínimo de calidad calculado por Kraken Bot para aceptar "
            "una señal. Use 0 para no filtrar por puntaje."
        )
        self.spnTP = QSpinBox()

        form.addRow("Modo de ejecuci\u00f3n", self.cboExecution)
        form.addRow("Riesgo", self.cboRiskMode)
        form.addRow("Máx. Operaciones", self.spnMaxTrades)
        form.addRow("Puntaje mínimo", self.spnScore)
        form.addRow("TP Objetivo", self.spnTP)

        section.addLayout(form)
        max_trades_label = form.labelForField(self.spnMaxTrades)
        if max_trades_label is not None:
            max_trades_label.setText("Máx. operaciones simultáneas")
            max_trades_label.setToolTip(self.spnMaxTrades.toolTip())
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
        self.lblMt5Capital = QLabel(
            "Capital MT5: seleccione una cuenta para consultar el saldo disponible."
        )
        self.lblMt5Capital.setWordWrap(True)
        self.lblMt5Capital.setToolTip(
            "El capital se toma del balance sincronizado de la cuenta MT5. "
            "No se configura manualmente en el perfil."
        )
        section.addWidget(self.lblMt5Capital)
        self.mt5Selector.selectionChanged.connect(self._update_mt5_capital)
        layout.addWidget(section)
        layout.addStretch()
        self.tabs.addTab(page, "MT5")

    def build_telegram_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        section = SectionWidget("Cuentas Telegram")
        self.telegramSelector = TelegramSelector()
        section.addWidget(self.telegramSelector)
        self.lblTelegramChannel = QLabel(
            "Seleccione primero una cuenta de Telegram para ver sus canales configurados."
        )
        self.cboTelegramChannel = QComboBox()
        self.cboTelegramChannel.setEnabled(False)
        self.cboTelegramChannel.setToolTip(
            "El canal seleccionado recibirá señales para este perfil. "
            "El mismo canal puede asignarse a otros perfiles."
        )
        section.addWidget(self.lblTelegramChannel)
        section.addWidget(self.cboTelegramChannel)
        self.telegramSelector.selectionChanged.connect(self._load_telegram_channels)
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
        self.txtComment.setText(profile.comment)
        self.spnMagic.setValue(profile.magic_number)
        execution_mode = profile.execution_mode or profile.operation_mode or "OFF"
        self.cboExecution.setCurrentText(execution_mode)
        self.cboMode.setCurrentText(execution_mode)
        risk_mode = profile.risk_mode if profile.risk_mode in {"PERCENT", "AMOUNT"} else "PERCENT"
        self.cboRiskMode.setCurrentText(risk_mode)
        self.spnMaxTrades.setValue(profile.max_open_trades)
        self.spnScore.setValue(profile.min_signal_score)
        self.spnTP.setValue(profile.tp_level)
        tp1_index = self.riskWidget.tp1Management.findData(
            getattr(profile, "tp1_management", "PROTECT_TP1")
        )
        self.riskWidget.tp1Management.setCurrentIndex(max(0, tp1_index))

        self._set_risk_widget_mode(risk_mode)
        if risk_mode == "PERCENT":
            self.riskWidget.value.setValue(profile.risk_percent)
        else:
            self.riskWidget.value.setValue(profile.risk_amount)
        daily_limit_enabled = (
            profile.max_daily_loss > 0 or profile.max_daily_profit > 0
        )
        self.riskWidget.daily.setChecked(daily_limit_enabled)
        self.riskWidget.dailyLossLimit.setValue(profile.max_daily_loss)
        self.riskWidget.dailyProfitLimit.setValue(profile.max_daily_profit)
        self.riskWidget.drawdown.setChecked(profile.max_drawdown > 0)
        self.riskWidget.drawdownLimit.setValue(profile.max_drawdown)

        self.mt5Selector.setSelected(self._as_id_list(profile.default_mt5_account))
        self.telegramSelector.setSelected(
            self._as_id_list(profile.telegram_account_id)
        )
        self._load_telegram_channels()
        selected_channel = self.cboTelegramChannel.findData(profile.telegram_channel_id)
        if selected_channel >= 0:
            self.cboTelegramChannel.setCurrentIndex(selected_channel)

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
            # Description is retained for compatibility with existing profiles;
            # comments are the single user-facing field for observations.
            "description": self.profile.description if self.profile else "",
            "comment": self.txtComment.text(),
            "operation_mode": self.cboExecution.currentText(),
            "magic_number": self.spnMagic.value(),
            "execution_mode": self.cboExecution.currentText(),
            "risk_mode": risk_mode,
            "risk_percent": risk_value if risk_mode == "PERCENT" else 0.0,
            "risk_amount": risk_value if risk_mode == "AMOUNT" else 0.0,
            "fixed_lot": self.profile.fixed_lot if self.profile else 0.0,
            "max_open_trades": self.spnMaxTrades.value(),
            "min_signal_score": self.spnScore.value(),
            "max_daily_loss": (
                self.riskWidget.dailyLossLimit.value()
                if self.riskWidget.daily.isChecked() else 0.0
            ),
            "max_daily_profit": (
                self.riskWidget.dailyProfitLimit.value()
                if self.riskWidget.daily.isChecked() else 0.0
            ),
            "max_drawdown": (
                self.riskWidget.drawdownLimit.value()
                if self.riskWidget.drawdown.isChecked() else 0.0
            ),
            "tp_level": self.spnTP.value(),
            "tp1_management": self.riskWidget.tp1Management.currentData(),
            "default_mt5_account": self._selected_account_id(self.mt5Selector),
            "telegram_account_id": self._selected_account_id(
                self.telegramSelector
            ),
            "telegram_channel_id": self.cboTelegramChannel.currentData(),
        }

    def set_mt5_accounts(self, accounts):
        self.mt5Selector.loadAccounts(accounts)
        self._update_mt5_capital()

    def _update_mt5_capital(self):
        accounts = self.mt5Selector.selectedAccounts()
        if not accounts:
            self.lblMt5Capital.setText(
                "Capital MT5: seleccione una cuenta para consultar el saldo disponible."
            )
            return

        balance = sum(float(getattr(account, "balance", 0.0) or 0.0) for account in accounts)
        connected = [account for account in accounts if getattr(account, "connected", False)]
        if connected:
            source = "saldo sincronizado"
        else:
            source = "último saldo guardado; conecte MT5 para actualizarlo"
        self.lblMt5Capital.setText(
            f"Capital MT5 ({len(accounts)} cuenta(s)): ${balance:,.2f} — {source}."
        )

    def set_telegram_accounts(self, accounts):
        self.telegramSelector.loadAccounts(accounts)
        self._load_telegram_channels()

    def _load_telegram_channels(self):
        account_id = self._selected_account_id(self.telegramSelector)
        previous_channel = self.cboTelegramChannel.currentData()
        self.cboTelegramChannel.clear()
        if account_id is None:
            self.cboTelegramChannel.setEnabled(False)
            self.lblTelegramChannel.setText(
                "Seleccione primero una cuenta de Telegram para ver sus canales configurados."
            )
            return

        channels = profile_telegram_channel_repository.get_available_channels(account_id)
        self.cboTelegramChannel.setEnabled(bool(channels))
        if not channels:
            self.lblTelegramChannel.setText(
                "Esta cuenta aún no tiene canales configurados. Agréguelos desde Canales."
            )
            return

        self.lblTelegramChannel.setText("Canal que utilizará este perfil")
        for channel in channels:
            title = channel.get("title") or channel.get("username") or str(channel["chat_id"])
            self.cboTelegramChannel.addItem(title, channel["chat_id"])
        index = self.cboTelegramChannel.findData(previous_channel)
        if index >= 0:
            self.cboTelegramChannel.setCurrentIndex(index)

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
            self._save_telegram_channel(profile)
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

    def _save_telegram_channel(self, profile):
        account_id = profile.telegram_account_id
        chat_id = profile.telegram_channel_id
        channel = None
        if account_id is not None and chat_id is not None:
            for candidate in profile_telegram_channel_repository.get_available_channels(account_id):
                if candidate["chat_id"] == chat_id:
                    channel = candidate
                    break
        profile_telegram_channel_repository.set_profile_channel(
            profile.id,
            account_id,
            channel,
        )

    def _set_risk_widget_mode(self, mode):
        buttons = {
            "PERCENT": self.riskWidget.percent,
            "AMOUNT": self.riskWidget.amount,
        }
        button = buttons.get(mode, self.riskWidget.percent)
        button.setChecked(True)
        self.riskWidget._update_value_presentation()

    def _sync_risk_mode(self, *_):
        self.cboRiskMode.setCurrentText(self._risk_mode())

    def _risk_mode(self):
        if self.riskWidget.amount.isChecked():
            return "AMOUNT"
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
