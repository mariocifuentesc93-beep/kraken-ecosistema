from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QPushButton,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
)

from dashboard.widgets.section_widget import SectionWidget
from dashboard.widgets.risk_widget import RiskWidget
from dashboard.widgets.account_selector import AccountSelector
from dashboard.widgets.telegram_selector import TelegramSelector
from dashboard.widgets.symbol_selector import SymbolSelector
from dashboard.widgets.statistics_panel import StatisticsPanel
from models.profile import Profile
from repositories.profile_repository import profile_repository
from PySide6.QtWidgets import QMessageBox


class ProfileDialog(QDialog):

    def __init__(self, profile=None, parent=None):

        super().__init__(parent)

        self.profile = profile

        self.setWindowTitle("Perfil Kraken")

        self.resize(1200, 850)

        self.build_ui()
    
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

        layout.addLayout(buttons)

        buttons.addStretch()

        self.btnDuplicate = QPushButton("Duplicar")

        self.btnExport = QPushButton("Exportar")

        self.btnImport = QPushButton("Importar")

        self.btnPreview = QPushButton("Vista previa")

        self.btnSave = QPushButton("Guardar")

        self.btnCancel = QPushButton("Cancelar")

        buttons.addWidget(self.btnDuplicate)

        buttons.addWidget(self.btnExport)

        buttons.addWidget(self.btnImport)

        buttons.addWidget(self.btnPreview)

        buttons.addWidget(self.btnSave)

        buttons.addWidget(self.btnCancel)

        self.btnCancel.clicked.connect(
            self.reject
        )

        self.btnSave.clicked.connect(
            self.save_profile
        )
    
    def build_general_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget(
            "Información General"
        )

        form = QFormLayout()

        self.txtName = QLineEdit()

        self.txtDescription = QTextEdit()

        self.cboMode = QComboBox()

        self.cboMode.addItems([
            "OFF",
            "SIMULATION",
            "DEMO",
            "LIVE"
        ])

        self.spnCapital = QDoubleSpinBox()

        self.spnCapital.setMaximum(
            999999999
        )

        self.spnMagic = QSpinBox()

        self.spnMagic.setMaximum(
            999999999
        )

        self.txtComment = QLineEdit()

        form.addRow(
            "Nombre",
            self.txtName
        )

        form.addRow(
            "Descripción",
            self.txtDescription
        )

        form.addRow(
            "Modo",
            self.cboMode
        )

        form.addRow(
            "Capital",
            self.spnCapital
        )

        form.addRow(
            "Magic Number",
            self.spnMagic
        )

        form.addRow(
            "Comentario",
            self.txtComment
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(
            page,
            "General"
        )

    def build_trading_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget(
            "Trading"
        )

        form = QFormLayout()

        self.cboExecution = QComboBox()

        self.cboExecution.addItems([
            "OFF",
            "SIMULATION",
            "DEMO",
            "LIVE"
        ])

        self.cboRiskMode = QComboBox()

        self.cboRiskMode.addItems([
            "PERCENT",
            "AMOUNT",
            "LOT"
        ])

        self.spnMaxTrades = QSpinBox()

        self.spnScore = QDoubleSpinBox()

        self.spnTP = QSpinBox()

        form.addRow(
            "Modo",
            self.cboExecution
        )

        form.addRow(
            "Riesgo",
            self.cboRiskMode
        )

        form.addRow(
            "Máx Operaciones",
            self.spnMaxTrades
        )

        form.addRow(
            "Score mínimo",
            self.spnScore
        )

        form.addRow(
            "TP Objetivo",
            self.spnTP
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Trading"
        )

    def build_risk_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        self.riskWidget = RiskWidget()

        layout.addWidget(
            self.riskWidget
        )

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Riesgo"
        )

    def build_mt5_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget(
            "Cuentas MT5"
        )

        self.mt5Selector = AccountSelector()

        section.addWidget(
            self.mt5Selector
        )

        layout.addWidget(
            section
        )

        layout.addStretch()

        self.tabs.addTab(
            page,
            "MT5"
        )

    def build_telegram_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget(
            "Cuentas Telegram"
        )

        self.telegramSelector = TelegramSelector()

        section.addWidget(
            self.telegramSelector
        )

        layout.addWidget(
            section
        )

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Telegram"
        )

    def build_symbols_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget(
            "Símbolos habilitados"
        )

        self.symbolSelector = SymbolSelector()

        section.addWidget(
            self.symbolSelector
        )

        layout.addWidget(
            section
        )

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Símbolos"
        )

    def build_statistics_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        self.statisticsPanel = StatisticsPanel()

        layout.addWidget(
            self.statisticsPanel
        )

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Estadísticas"
        )

    def build_audit_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget(
            "Auditoría"
        )

        self.lblCreated = QLabel("-")

        self.lblUpdated = QLabel("-")

        self.lblOperations = QLabel("0")

        self.lblProfit = QLabel("0")

        self.lblWinRate = QLabel("0 %")

        form = QFormLayout()

        form.addRow(
            "Creado",
            self.lblCreated
        )

        form.addRow(
            "Actualizado",
            self.lblUpdated
        )

        form.addRow(
            "Operaciones",
            self.lblOperations
        )

        form.addRow(
            "Profit",
            self.lblProfit
        )

        form.addRow(
            "Win Rate",
            self.lblWinRate
        )

        section.addLayout(
            form
        )

        layout.addWidget(
            section
        )

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Auditoría"
        )

    def load_profile(self, profile):

        if profile is None:

            return

        self.profile = profile

        self.txtName.setText(profile.name)
        self.txtDescription.setPlainText(profile.description)
        self.txtComment.setText(profile.comment)

        self.spnMagic.setValue(profile.magic_number)

        self.cboExecution.setCurrentText(profile.execution_mode)

        self.cboRiskMode.setCurrentText(profile.risk_mode)

        self.spnTP.setValue(profile.tp_level)

        self.lblCreated.setText(str(profile.created_at))
        self.lblUpdated.setText(str(profile.updated_at))

        # Riesgo
        if profile.risk_mode == "PERCENT":
          self.riskWidget.percent.setChecked(True)

        elif profile.risk_mode == "AMOUNT":
          self.riskWidget.amount.setChecked(True)

        else:
          self.riskWidget.lot.setChecked(True)


        if profile.risk_mode == "PERCENT":
          self.riskWidget.value.setValue(profile.risk_percent)

        elif profile.risk_mode == "AMOUNT":
          self.riskWidget.value.setValue(profile.risk_amount)

        else:
          self.riskWidget.value.setValue(profile.fixed_lot)

        # Cuenta MT5
          self.mt5Selector.setSelectedAccount(
        profile.default_mt5_account
        )

        # Cuenta Telegram
          self.telegramSelector.setSelectedAccount(
        profile.telegram_account_id
        )

        # Símbolos habilitados
          self.symbolSelector.loadProfile(profile)


    def get_profile_data(self):

    return {

        "name": self.txtName.text(),

        "description": self.txtDescription.toPlainText(),

        "comment": self.txtComment.text(),

        "magic_number": self.spnMagic.value(),

        "execution_mode": self.cboExecution.currentText(),

        "risk_mode": self.cboRiskMode.currentText(),

        "tp_level": self.spnTP.value(),

        "default_mt5_account": self.mt5Selector.selectedAccount(),

        "telegram_account_id": self.telegramSelector.selectedAccount()
    }

    def set_mt5_accounts(self, accounts):

        self.mt5Selector.loadAccounts(
            accounts
        )

    def set_telegram_accounts(self, accounts):

        self.telegramSelector.loadAccounts(
            accounts
        )

    def set_symbols(self, symbols):

        self.symbolSelector.loadSymbols(
            symbols
        )

    def set_statistics(self, stats):

        if not stats:

            self.statisticsPanel.clear()

            return

        for key, value in stats.items():

            self.statisticsPanel.setValue(
                key,
                value,
            )

    def set_audit_data(self, audit):

        if not audit:

            return

        self.lblCreated.setText(
            str(audit.get("created_at", "-"))
        )

        self.lblUpdated.setText(
            str(audit.get("updated_at", "-"))
        )

        self.lblOperations.setText(
            str(audit.get("operations", 0))
        )

        self.lblProfit.setText(
            str(audit.get("profit", 0))
        )

        self.lblWinRate.setText(
            f'{audit.get("win_rate", 0)} %'
        )

    def save_profile(self):

        nombre = self.txtName.text().strip()

    if not nombre:

        QMessageBox.warning(
            self,
            "Perfil",
            "Debe ingresar un nombre."
        )
        return

    if self.profile is None:
        self.profile = Profile()

    # Información general
        self.profile.name = nombre
        self.profile.description = self.txtDescription.toPlainText()
        self.profile.comment = self.txtComment.text()

    # Trading
        self.profile.magic_number = self.spnMagic.value()
        self.profile.execution_mode = self.cboExecution.currentText()
        self.profile.risk_mode = self.cboRiskMode.currentText()
        self.profile.tp_level = self.spnTP.value()

    # MT5
        self.profile.default_mt5_account = (
        self.mt5Selector.selectedAccount()
    )

    # Telegram
        self.profile.telegram_account_id = (
        self.telegramSelector.selectedAccount()
    )

    # Estado
        self.profile.enabled = True

    if not hasattr(self.profile, "active"):
        self.profile.active = True

    if self.profile.id:
        profile_repository.update(self.profile)
    else:
        profile_repository.create(self.profile)

    self.accept()

