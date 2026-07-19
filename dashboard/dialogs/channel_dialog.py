from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QPushButton,
    QLabel,
    QLineEdit,
    QTextEdit,
    QFormLayout,
    QCheckBox,
    QComboBox,
    QSpinBox,
)

from dashboard.widgets.section_widget import SectionWidget
from dashboard.widgets.connection_indicator import ConnectionIndicator


class ChannelDialog(QDialog):

    def __init__(self, channel=None, parent=None):

        super().__init__(parent)

        self.channel = channel

        self.setWindowTitle("Canal Telegram")

        self.resize(1000, 720)

        self.build_ui()

        if channel is not None:
            self.load_channel(channel)

    # ---------------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()

        layout.addWidget(self.tabs)

        self.build_general_tab()

        self.build_profile_tab()

        self.build_options_tab()

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

    # ---------------------------------------------------------

    def build_general_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        self.connection = ConnectionIndicator(
            "Canal Telegram"
        )

        layout.addWidget(self.connection)

        section = SectionWidget(
            "Información"
        )

        form = QFormLayout()

        self.txtName = QLineEdit()

        self.txtChatId = QLineEdit()

        self.txtUsername = QLineEdit()

        self.txtDescription = QTextEdit()

        self.chkEnabled = QCheckBox(
            "Canal habilitado"
        )

        form.addRow("Nombre", self.txtName)

        form.addRow("Chat ID", self.txtChatId)

        form.addRow("Username", self.txtUsername)

        form.addRow("Descripción", self.txtDescription)

        form.addRow("", self.chkEnabled)

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(page, "General")

    # ---------------------------------------------------------

    def build_profile_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget(
            "Perfil asociado"
        )

        form = QFormLayout()

        self.cboProfile = QComboBox()

        self.cboPriority = QComboBox()

        self.cboPriority.addItems([

            "Muy Alta",

            "Alta",

            "Normal",

            "Baja"

        ])

        form.addRow(
            "Perfil",
            self.cboProfile
        )

        form.addRow(
            "Prioridad",
            self.cboPriority
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Perfil"
        )

    # ---------------------------------------------------------

    def build_options_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget(
            "Opciones"
        )

        form = QFormLayout()

        self.chkReadHistory = QCheckBox(
            "Leer historial"
        )

        self.chkNotifications = QCheckBox(
            "Notificaciones"
        )

        self.chkValidateSignals = QCheckBox(
            "Validar señales"
        )

        self.chkAutoSync = QCheckBox(
            "Sincronizar automáticamente"
        )

        self.spnRefresh = QSpinBox()

        self.spnRefresh.setValue(30)

        form.addRow(
            "",
            self.chkReadHistory
        )

        form.addRow(
            "",
            self.chkNotifications
        )

        form.addRow(
            "",
            self.chkValidateSignals
        )

        form.addRow(
            "",
            self.chkAutoSync
        )

        form.addRow(
            "Actualizar (s)",
            self.spnRefresh
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Opciones"
        )

    # ---------------------------------------------------------

    def build_statistics_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget(
            "Estadísticas"
        )

        form = QFormLayout()

        self.lblSignals = QLabel("0")

        self.lblExecuted = QLabel("0")

        self.lblIgnored = QLabel("0")

        self.lblWinRate = QLabel("0 %")

        self.lblLastSignal = QLabel("-")

        form.addRow(
            "Señales",
            self.lblSignals
        )

        form.addRow(
            "Ejecutadas",
            self.lblExecuted
        )

        form.addRow(
            "Ignoradas",
            self.lblIgnored
        )

        form.addRow(
            "Win Rate",
            self.lblWinRate
        )

        form.addRow(
            "Última señal",
            self.lblLastSignal
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Estadísticas"
        )

    def load_channel(self, channel):

        if channel is None:

            return

        self.channel = channel

        data = channel if isinstance(channel, dict) else vars(channel)

        self.txtName.setText(data.get("title", data.get("name", "")))

        self.txtChatId.setText(
            str(data.get("chat_id", ""))
        )

        self.txtUsername.setText(
            data.get("username", "")
        )

        self.txtDescription.setPlainText(
            data.get("description", "")
        )

        self.chkEnabled.setChecked(
            bool(data.get("enabled", True))
        )

        index = self.cboProfile.findData(data.get("profile_id"))
        if index >= 0:
            self.cboProfile.setCurrentIndex(index)

        self.cboPriority.setCurrentIndex(
            max(0, min(int(data.get("priority", 1)) - 1, 3))
        )

    def set_profiles(self, profiles):
        self.cboProfile.clear()
        for profile in profiles:
            self.cboProfile.addItem(profile.display_name, profile.id)
    
    def get_channel_data(self):

        return {

            "name":
                self.txtName.text(),

            "chat_id":
                self.txtChatId.text(),

            "username":
                self.txtUsername.text(),

            "description":
                self.txtDescription.toPlainText(),

            "enabled":
                self.chkEnabled.isChecked(),

            "profile":
                self.cboProfile.currentData(),

            "priority":
                self.cboPriority.currentIndex(),

            "read_history":
                self.chkReadHistory.isChecked(),

            "notifications":
                self.chkNotifications.isChecked(),

            "validate_signals":
                self.chkValidateSignals.isChecked(),

            "auto_sync":
                self.chkAutoSync.isChecked(),

            "refresh":
                self.spnRefresh.value()

        }

    def validate(self):

        if not self.txtName.text().strip():

            self.tabs.setCurrentIndex(0)

            self.txtName.setFocus()

            return False

        if not self.txtChatId.text().strip():

            self.tabs.setCurrentIndex(0)

            self.txtChatId.setFocus()

            return False

        return True

    def accept(self):

        if not self.validate():

            return

        super().accept()

