from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QPushButton,
    QLabel,
    QLineEdit,
    QFormLayout,
    QSpinBox,
    QComboBox,
    QCheckBox,
    QDoubleSpinBox,
)

from dashboard.widgets.section_widget import SectionWidget
from dashboard.widgets.connection_indicator import ConnectionIndicator
from dashboard.dialogs.dialog_layout import fit_dialog_to_screen


class MT5AccountDialog(QDialog):

    def __init__(self, account=None, parent=None):

        super().__init__(parent)

        self.account = account

        self.setWindowTitle("Cuenta MetaTrader 5")

        fit_dialog_to_screen(self, 900, 680)

        self.build_ui()

        if account is not None:
            self.load_account(account)

    # ---------------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()

        layout.addWidget(self.tabs)

        self.build_general_tab()

        self.build_connection_tab()

        self.build_trading_tab()

        self.build_advanced_tab()

        buttons = QHBoxLayout()

        layout.addLayout(buttons)

        buttons.addStretch()

        self.btnSave = QPushButton("Guardar")

        self.btnCancel = QPushButton("Cancelar")

        buttons.addWidget(self.btnSave)

        buttons.addWidget(self.btnCancel)

        self.btnCancel.clicked.connect(
            self.reject
        )

        self.btnSave.clicked.connect(
            self.accept
        )

    # ---------------------------------------------------------

    def build_general_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget(
            "Información General"
        )

        form = QFormLayout()

        self.txtName = QLineEdit()

        self.chkEnabled = QCheckBox(
            "Cuenta habilitada"
        )

        self.cboEnvironment = QComboBox()

        self.cboEnvironment.addItems([
            "LIVE",
            "DEMO"
        ])

        form.addRow(
            "Nombre",
            self.txtName
        )

        form.addRow(
            "Entorno",
            self.cboEnvironment
        )

        form.addRow(
            "",
            self.chkEnabled
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(
            page,
            "General"
        )

    # ---------------------------------------------------------

    def build_connection_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        self.connection = ConnectionIndicator(
            "MetaTrader 5"
        )

        layout.addWidget(
            self.connection
        )

        section = SectionWidget(
            "Conexión"
        )

        form = QFormLayout()

        self.txtLogin = QLineEdit()

        self.txtPassword = QLineEdit()

        self.txtPassword.setEchoMode(
            QLineEdit.Password
        )

        self.txtServer = QLineEdit()

        self.txtTerminal = QLineEdit()

        form.addRow(
            "Login",
            self.txtLogin
        )

        form.addRow(
            "Contraseña",
            self.txtPassword
        )

        form.addRow(
            "Servidor",
            self.txtServer
        )

        form.addRow(
            "Terminal",
            self.txtTerminal
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Conexión"
        )

    # ---------------------------------------------------------

    def build_trading_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget(
            "Trading"
        )

        form = QFormLayout()

        self.spnSlippage = QSpinBox()

        self.spnDeviation = QSpinBox()

        self.cboFill = QComboBox()

        self.cboFill.addItems([
            "IOC",
            "FOK",
            "RETURN"
        ])

        self.cboExecution = QComboBox()

        self.cboExecution.addItems([
            "MARKET",
            "INSTANT"
        ])

        form.addRow(
            "Slippage",
            self.spnSlippage
        )

        form.addRow(
            "Deviation",
            self.spnDeviation
        )

        form.addRow(
            "Fill Policy",
            self.cboFill
        )

        form.addRow(
            "Execution",
            self.cboExecution
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Trading"
        )

    # ---------------------------------------------------------

    def build_advanced_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget(
            "Opciones Avanzadas"
        )

        form = QFormLayout()

        self.spnReconnect = QSpinBox()

        self.spnReconnect.setValue(10)

        self.spnTimeout = QSpinBox()

        self.spnTimeout.setValue(30)

        self.spnHeartbeat = QSpinBox()

        self.spnHeartbeat.setValue(5)

        self.chkAutoReconnect = QCheckBox(
            "Reconexión automática"
        )

        self.chkAutoReconnect.setChecked(True)

        self.spnMaxRetries = QSpinBox()

        self.spnMaxRetries.setValue(5)

        self.spnCommission = QDoubleSpinBox()

        self.spnCommission.setDecimals(2)

        self.spnCommission.setMaximum(
            99999
        )

        form.addRow(
            "Timeout (s)",
            self.spnTimeout
        )

        form.addRow(
            "Heartbeat (s)",
            self.spnHeartbeat
        )

        form.addRow(
            "Reconectar (s)",
            self.spnReconnect
        )

        form.addRow(
            "Máx. reintentos",
            self.spnMaxRetries
        )

        form.addRow(
            "Comisión",
            self.spnCommission
        )

        form.addRow(
            "",
            self.chkAutoReconnect
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Avanzado"
        )

    def load_account(self, account):

        if account is None:

            return

        self.account = account

        self.txtName.setText(
            getattr(account, "name", "")
        )

        self.txtLogin.setText(
            str(getattr(account, "login", ""))
        )

        self.txtPassword.setText(
            getattr(account, "password", "")
        )

        self.txtServer.setText(
            getattr(account, "server", "")
        )

        self.txtTerminal.setText(
            getattr(account, "terminal_path", "")
        )

        self.chkEnabled.setChecked(
            getattr(account, "active", True)
        )

        self.cboEnvironment.setCurrentText(
            getattr(account, "execution_mode", "LIVE")
        )

        self.spnSlippage.setValue(
            getattr(account, "slippage", 5)
        )

        self.spnDeviation.setValue(
            getattr(account, "deviation", 10)
        )

        self.cboFill.setCurrentText(
            getattr(account, "fill_policy", "IOC")
        )

        self.cboExecution.setCurrentText(
            getattr(account, "execution_type", "MARKET")
        )

        self.spnTimeout.setValue(
            getattr(account, "timeout", 30)
        )

        self.spnReconnect.setValue(
            getattr(account, "reconnect_interval", 10)
        )

        self.spnHeartbeat.setValue(
            getattr(account, "heartbeat", 5)
        )

        self.spnMaxRetries.setValue(
            getattr(account, "max_retries", 5)
        )

        self.spnCommission.setValue(
            getattr(account, "commission", 0)
        )

        self.chkAutoReconnect.setChecked(
            getattr(account, "auto_reconnect", True)
        )

    def get_account_data(self):

        return {

            "name":
                self.txtName.text().strip(),

            "login":
                self.txtLogin.text().strip(),

            "password":
                self.txtPassword.text(),

            "server":
                self.txtServer.text().strip(),

            "terminal_path":
                self.txtTerminal.text().strip(),

            "enabled":
                self.chkEnabled.isChecked(),

            "environment":
                self.cboEnvironment.currentText(),

            "slippage":
                self.spnSlippage.value(),

            "deviation":
                self.spnDeviation.value(),

            "fill_policy":
                self.cboFill.currentText(),

            "execution_type":
                self.cboExecution.currentText(),

            "timeout":
                self.spnTimeout.value(),

            "heartbeat":
                self.spnHeartbeat.value(),

            "reconnect_interval":
                self.spnReconnect.value(),

            "max_retries":
                self.spnMaxRetries.value(),

            "commission":
                self.spnCommission.value(),

            "auto_reconnect":
                self.chkAutoReconnect.isChecked(),

        }

    def validate(self):

        if not self.txtName.text().strip():

            self.txtName.setFocus()

            return False

        if not self.txtLogin.text().strip():

            self.tabs.setCurrentIndex(1)

            self.txtLogin.setFocus()

            return False

        if not self.txtPassword.text():

            self.tabs.setCurrentIndex(1)

            self.txtPassword.setFocus()

            return False

        if not self.txtServer.text().strip():

            self.tabs.setCurrentIndex(1)

            self.txtServer.setFocus()

            return False

        return True

    def accept(self):

        if not self.validate():

            return

        super().accept()

    def set_connection_status(
        self,
        status,
        message="",
    ):

        self.connection.setStatus(
            status
        )

        self.connection.setSubtitle(
            message
        )

    def test_connection_result(
        self,
        success,
        message,
    ):

        if success:

            self.set_connection_status(
                "ONLINE",
                message,
            )

        else:

            self.set_connection_status(
                "ERROR",
                message,
            )
            
    def test_connection(self):

        if not self.validate():

            return

        self.set_connection_status(
            "WARNING",
            "Probando conexión..."
        )

        #
        # Aquí se llamará posteriormente al
        # MT5Connector.connect(...)
        #
        # Ejemplo:
        #
        # connector = MT5Connector()
        # ok, msg = connector.test(...)
        # self.test_connection_result(ok, msg)
        #

        self.test_connection_result(
            True,
            "Conexión simulada correctamente."
        )

