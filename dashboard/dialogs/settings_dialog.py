from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QPushButton,
    QLabel,
    QFormLayout,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QLineEdit,
)

from dashboard.widgets.section_widget import SectionWidget


class SettingsDialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Configuración General")

        self.resize(1100, 820)

        self.build_ui()

    # ------------------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()

        layout.addWidget(self.tabs)

        self.build_general_tab()

        self.build_trading_tab()

        self.build_mt5_tab()

        self.build_telegram_tab()

        self.build_logs_tab()

        self.build_database_tab()

        self.build_backup_tab()

        self.build_performance_tab()

        buttons = QHBoxLayout()

        buttons.addStretch()

        self.btnSave = QPushButton("Guardar")

        self.btnCancel = QPushButton("Cancelar")

        buttons.addWidget(self.btnSave)

        buttons.addWidget(self.btnCancel)

        layout.addLayout(buttons)

        self.btnSave.clicked.connect(self.accept)

        self.btnCancel.clicked.connect(self.reject)

    def build_general_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget("General")

        form = QFormLayout()

        self.cboLanguage = QComboBox()

        self.cboLanguage.addItems([
            "Español",
            "English"
        ])

        self.cboTheme = QComboBox()

        self.cboTheme.addItems([
            "Claro",
            "Oscuro",
            "Sistema"
        ])

        self.chkStartWindows = QCheckBox(
            "Iniciar con Windows"
        )

        self.chkMinimizeTray = QCheckBox(
            "Minimizar al área de notificación"
        )

        form.addRow(
            "Idioma",
            self.cboLanguage
        )

        form.addRow(
            "Tema",
            self.cboTheme
        )

        form.addRow(
            "",
            self.chkStartWindows
        )

        form.addRow(
            "",
            self.chkMinimizeTray
        )

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

        self.cboExecution.addItems([
            "OFF",
            "SIMULATION",
            "DEMO",
            "LIVE"
        ])

        self.cboRisk = QComboBox()

        self.cboRisk.addItems([
            "PERCENT",
            "AMOUNT",
            "LOT"
        ])

        self.spnRisk = QDoubleSpinBox()

        self.spnRisk.setMaximum(100)

        self.spnTP = QSpinBox()

        self.spnTP.setMaximum(10)

        self.chkCloseTP1 = QCheckBox(
            "Cerrar en TP1"
        )

        form.addRow(
            "Modo",
            self.cboExecution
        )

        form.addRow(
            "Tipo riesgo",
            self.cboRisk
        )

        form.addRow(
            "Valor",
            self.spnRisk
        )

        form.addRow(
            "TP",
            self.spnTP
        )

        form.addRow(
            "",
            self.chkCloseTP1
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(page, "Trading")

    def build_mt5_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget("MetaTrader 5")

        form = QFormLayout()

        self.spnReconnect = QSpinBox()

        self.spnReconnect.setValue(10)

        self.spnHeartbeat = QSpinBox()

        self.spnHeartbeat.setValue(5)

        self.chkReconnect = QCheckBox(
            "Reconectar automáticamente"
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
            self.chkReconnect
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(page, "MT5")

    def build_telegram_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget("Telegram")

        form = QFormLayout()

        self.chkAutoConnect = QCheckBox(
            "Conectar automáticamente"
        )

        self.chkAutoSync = QCheckBox(
            "Sincronizar canales"
        )

        self.spnTelegramHeartbeat = QSpinBox()

        self.spnTelegramHeartbeat.setValue(5)

        form.addRow(
            "",
            self.chkAutoConnect
        )

        form.addRow(
            "",
            self.chkAutoSync
        )

        form.addRow(
            "Heartbeat",
            self.spnTelegramHeartbeat
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(page, "Telegram")

    def build_logs_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget("Logs")

        form = QFormLayout()

        self.cboLogLevel = QComboBox()

        self.cboLogLevel.addItems([
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR"
        ])

        self.chkFileLog = QCheckBox(
            "Guardar en archivo"
        )

        self.chkConsoleLog = QCheckBox(
            "Mostrar consola"
        )

        form.addRow(
            "Nivel",
            self.cboLogLevel
        )

        form.addRow(
            "",
            self.chkFileLog
        )

        form.addRow(
            "",
            self.chkConsoleLog
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(page, "Logs")

    def build_database_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget(
            "Base de Datos"
        )

        form = QFormLayout()

        self.txtDatabase = QLineEdit()

        self.chkAutoVacuum = QCheckBox(
            "Optimizar automáticamente"
        )

        self.chkAutoCommit = QCheckBox(
            "Guardar automáticamente"
        )

        self.spnCommitInterval = QSpinBox()

        self.spnCommitInterval.setRange(1, 3600)

        self.spnCommitInterval.setValue(30)

        form.addRow(
            "Archivo",
            self.txtDatabase
        )

        form.addRow(
            "",
            self.chkAutoVacuum
        )

        form.addRow(
            "",
            self.chkAutoCommit
        )

        form.addRow(
            "Guardar cada (s)",
            self.spnCommitInterval
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Base de Datos"
        )

    def build_backup_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget(
            "Respaldos"
        )

        form = QFormLayout()

        self.chkAutoBackup = QCheckBox(
            "Respaldo automático"
        )

        self.spnBackupHours = QSpinBox()

        self.spnBackupHours.setRange(1, 168)

        self.spnBackupHours.setValue(24)

        self.txtBackupFolder = QLineEdit()

        self.spnKeepBackups = QSpinBox()

        self.spnKeepBackups.setRange(1, 500)

        self.spnKeepBackups.setValue(30)

        form.addRow(
            "",
            self.chkAutoBackup
        )

        form.addRow(
            "Cada (horas)",
            self.spnBackupHours
        )

        form.addRow(
            "Carpeta",
            self.txtBackupFolder
        )

        form.addRow(
            "Conservar",
            self.spnKeepBackups
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Respaldos"
        )

    def build_performance_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget(
            "Rendimiento"
        )

        form = QFormLayout()

        self.spnThreads = QSpinBox()

        self.spnThreads.setRange(1, 64)

        self.spnThreads.setValue(4)

        self.spnRefresh = QSpinBox()

        self.spnRefresh.setRange(100, 10000)

        self.spnRefresh.setValue(1000)

        self.chkCache = QCheckBox(
            "Usar caché"
        )

        self.chkLazyLoading = QCheckBox(
            "Carga diferida"
        )

        self.chkRealtime = QCheckBox(
            "Actualización en tiempo real"
        )

        form.addRow(
            "Hilos",
            self.spnThreads
        )

        form.addRow(
            "Actualizar (ms)",
            self.spnRefresh
        )

        form.addRow(
            "",
            self.chkCache
        )

        form.addRow(
            "",
            self.chkLazyLoading
        )

        form.addRow(
            "",
            self.chkRealtime
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Rendimiento"
        )

    def load_settings(self, settings):

        if not settings:

            return

        for key, value in settings.items():

            widget = getattr(
                self,
                key,
                None
            )

            if widget is None:

                continue

            if isinstance(widget, QLineEdit):

                widget.setText(str(value))

            elif isinstance(widget, QCheckBox):

                widget.setChecked(bool(value))

            elif isinstance(widget, QSpinBox):

                widget.setValue(int(value))

            elif isinstance(widget, QDoubleSpinBox):

                widget.setValue(float(value))

            elif isinstance(widget, QComboBox):

                widget.setCurrentText(str(value))

    def get_settings(self):

        return {

            "cboLanguage":
                self.cboLanguage.currentText(),

            "cboTheme":
                self.cboTheme.currentText(),

            "chkStartWindows":
                self.chkStartWindows.isChecked(),

            "chkMinimizeTray":
                self.chkMinimizeTray.isChecked(),

            "cboExecution":
                self.cboExecution.currentText(),

            "cboRisk":
                self.cboRisk.currentText(),

            "spnRisk":
                self.spnRisk.value(),

            "spnTP":
                self.spnTP.value(),

            "chkCloseTP1":
                self.chkCloseTP1.isChecked(),

            "spnReconnect":
                self.spnReconnect.value(),

            "spnHeartbeat":
                self.spnHeartbeat.value(),

            "chkReconnect":
                self.chkReconnect.isChecked(),

            "chkAutoConnect":
                self.chkAutoConnect.isChecked(),

            "chkAutoSync":
                self.chkAutoSync.isChecked(),

            "spnTelegramHeartbeat":
                self.spnTelegramHeartbeat.value(),

            "cboLogLevel":
                self.cboLogLevel.currentText(),

            "chkFileLog":
                self.chkFileLog.isChecked(),

            "chkConsoleLog":
                self.chkConsoleLog.isChecked(),

            "txtDatabase":
                self.txtDatabase.text(),

            "chkAutoVacuum":
                self.chkAutoVacuum.isChecked(),

            "chkAutoCommit":
                self.chkAutoCommit.isChecked(),

            "spnCommitInterval":
                self.spnCommitInterval.value(),

            "chkAutoBackup":
                self.chkAutoBackup.isChecked(),

            "spnBackupHours":
                self.spnBackupHours.value(),

            "txtBackupFolder":
                self.txtBackupFolder.text(),

            "spnKeepBackups":
                self.spnKeepBackups.value(),

            "spnThreads":
                self.spnThreads.value(),

            "spnRefresh":
                self.spnRefresh.value(),

            "chkCache":
                self.chkCache.isChecked(),

            "chkLazyLoading":
                self.chkLazyLoading.isChecked(),

            "chkRealtime":
                self.chkRealtime.isChecked(),

        }

