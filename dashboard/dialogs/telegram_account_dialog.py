from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QPushButton,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QCheckBox,
    QSpinBox,
)

from dashboard.widgets.section_widget import SectionWidget
from dashboard.widgets.connection_indicator import ConnectionIndicator
from dashboard.dialogs.dialog_layout import fit_dialog_to_screen


class TelegramAccountDialog(QDialog):

    def __init__(self, account=None, parent=None):

        super().__init__(parent)

        self.account = account

        self.setWindowTitle("Cuenta Telegram")

        fit_dialog_to_screen(self, 950, 680)

        self.build_ui()

        if account is not None:
            self.load_account(account)

    # --------------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()

        layout.addWidget(self.tabs)

        self.build_general_tab()

        self.build_api_tab()

        self.build_session_tab()

        self.build_advanced_tab()

        buttons = QHBoxLayout()

        buttons.addStretch()

        self.btnSave = QPushButton("Guardar")

        self.btnCancel = QPushButton("Cancelar")

        buttons.addWidget(self.btnSave)

        buttons.addWidget(self.btnCancel)

        layout.addLayout(buttons)

        self.btnSave.clicked.connect(
            self.accept
        )

        self.btnCancel.clicked.connect(
            self.reject
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

        self.chkEnabled = QCheckBox(
            "Cuenta habilitada"
        )
        self.chkEnabled.setChecked(True)

        form.addRow(
            "Nombre",
            self.txtName
        )

        form.addRow(
            "Descripción",
            self.txtDescription
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

    def build_api_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        self.connection = ConnectionIndicator(
            "Telegram API"
        )

        layout.addWidget(
            self.connection
        )

        section = SectionWidget(
            "API Telegram"
        )

        form = QFormLayout()

        self.txtApiId = QLineEdit()

        self.txtApiHash = QLineEdit()

        self.txtPhone = QLineEdit()

        form.addRow(
            "API ID",
            self.txtApiId
        )

        form.addRow(
            "API HASH",
            self.txtApiHash
        )

        form.addRow(
            "Teléfono",
            self.txtPhone
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(
            page,
            "API"
        )

        self.connection.testRequested.connect(
            self.test_connection
        )

    def build_session_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget(
            "Sesión Telethon"
        )

        form = QFormLayout()

        self.txtSession = QLineEdit()

        self.lblStatus = QLabel(
            "Sin sesión"
        )

        self.btnLogin = QPushButton(
            "Iniciar sesión"
        )

        self.btnLogout = QPushButton(
            "Cerrar sesión"
        )

        form.addRow(
            "Archivo sesión",
            self.txtSession
        )

        form.addRow(
            "Estado",
            self.lblStatus
        )

        section.addLayout(form)

        buttons = QHBoxLayout()

        buttons.addWidget(
            self.btnLogin
        )

        buttons.addWidget(
            self.btnLogout
        )

        section.addLayout(
            buttons
        )

        layout.addWidget(
            section
        )

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Sesión"
        )

        self.btnLogin.clicked.connect(
            self.login
        )

        self.btnLogout.clicked.connect(
            self.logout
        )

    def build_advanced_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget(
            "Configuración Avanzada"
        )

        form = QFormLayout()

        self.spnReconnect = QSpinBox()

        self.spnReconnect.setValue(10)

        self.spnHeartbeat = QSpinBox()

        self.spnHeartbeat.setValue(5)

        self.chkAutoReconnect = QCheckBox(
            "Reconectar automáticamente"
        )

        self.chkAutoReconnect.setChecked(
            True
        )

        self.chkReceiveMessages = QCheckBox(
            "Recibir mensajes"
        )

        self.chkReceiveMessages.setChecked(
            True
        )

        form.addRow(
            "Reconectar (s)",
            self.spnReconnect
        )

        form.addRow(
            "Heartbeat",
            self.spnHeartbeat
        )

        form.addRow(
            "",
            self.chkAutoReconnect
        )

        form.addRow(
            "",
            self.chkReceiveMessages
        )

        section.addLayout(form)

        layout.addWidget(
            section
        )

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

        self.txtDescription.setPlainText(
            getattr(account, "description", "")
        )

        self.chkEnabled.setChecked(
            getattr(account, "enabled", True)
        )

        self.txtApiId.setText(
            str(getattr(account, "api_id", ""))
        )

        self.txtApiHash.setText(
            getattr(account, "api_hash", "")
        )

        self.txtPhone.setText(
            getattr(account, "phone", "")
        )

        self.txtSession.setText(
            getattr(account, "session_name", "")
        )

        self.spnReconnect.setValue(
            getattr(account, "reconnect_interval", 10)
        )

        self.spnHeartbeat.setValue(
            getattr(account, "heartbeat", 5)
        )

        self.chkAutoReconnect.setChecked(
            getattr(account, "auto_reconnect", True)
        )

        self.chkReceiveMessages.setChecked(
            getattr(account, "receive_messages", True)
        )

        if getattr(account, "connected", False):

            self.lblStatus.setText(
                "Sesión iniciada"
            )

            self.connection.setStatus(
                "ONLINE"
            )

        else:

            self.lblStatus.setText(
                "Sin sesión"
            )

            self.connection.setStatus(
                "OFFLINE"
            )

    def get_account_data(self):

        return {

            "name":
                self.txtName.text().strip(),

            "description":
                self.txtDescription.toPlainText(),

            "enabled":
                self.chkEnabled.isChecked(),

            "api_id":
                self.txtApiId.text().strip(),

            "api_hash":
                self.txtApiHash.text().strip(),

            "phone":
                self.txtPhone.text().strip(),

            "session_name":
                self.txtSession.text().strip(),

            "reconnect_interval":
                self.spnReconnect.value(),

            "heartbeat":
                self.spnHeartbeat.value(),

            "auto_reconnect":
                self.chkAutoReconnect.isChecked(),

            "receive_messages":
                self.chkReceiveMessages.isChecked()

        }

    def validate(self):

        if not self.txtName.text().strip():

            self.tabs.setCurrentIndex(0)

            self.txtName.setFocus()

            return False

        if not self.txtApiId.text().strip():

            self.tabs.setCurrentIndex(1)

            self.txtApiId.setFocus()

            return False

        if not self.txtApiHash.text().strip():

            self.tabs.setCurrentIndex(1)

            self.txtApiHash.setFocus()

            return False

        if not self.txtPhone.text().strip():

            self.tabs.setCurrentIndex(1)

            self.txtPhone.setFocus()

            return False

        return True

    def accept(self):

        if not self.validate():

            return

        super().accept()

    def set_connection_status(
        self,
        status,
        message=""
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
        message
    ):

        if success:

            self.connection.setStatus(
                "ONLINE"
            )

            self.lblStatus.setText(
                "Conectado"
            )

        else:

            self.connection.setStatus(
                "ERROR"
            )

            self.lblStatus.setText(
                "Error"

            )

        self.connection.setSubtitle(
            message
        )

    def test_connection(self):

        if not self.validate():

            return

        self.set_connection_status(

            "WARNING",

            "Conectando con Telegram..."

        )

        #
        # Aquí se conectará posteriormente:
        #
        # TelegramAccountManager
        #
        # ok, msg = manager.test(...)
        #

        self.test_connection_result(

            True,

            "Conexión simulada correctamente."

        )

    def login(self):

        if not self.validate():

            return

        self.lblStatus.setText(
            "Autenticando..."
        )

        #
        # manager.login(...)
        #

        self.connection.setStatus(
            "ONLINE"
        )

        self.lblStatus.setText(
            "Sesión iniciada"
        )

    def logout(self):

        #
        # manager.logout(...)
        #

        self.connection.setStatus(
            "OFFLINE"
        )

        self.lblStatus.setText(
            "Sin sesión"
        )

    def sync_channels(self):

        #
        # manager.sync_channels(...)
        #

        self.connection.setSubtitle(

            "Canales sincronizados."

        )

        self.btnLogin.clicked.connect(
            self.login
        )

        self.btnLogout.clicked.connect(
            self.logout
        )

