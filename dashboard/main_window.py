from datetime import datetime
from pathlib import Path
import shutil

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QToolBar,
    QStatusBar,
    QLabel,
    QDockWidget,
    QTextEdit,
    QFileDialog,
    QMessageBox,
)

from dashboard.pages.dashboard_page import DashboardPage
from dashboard.pages.operations_page import OperationsPage
from dashboard.pages.statistics_page import StatisticsPage
from dashboard.pages.profiles_page import ProfilesPage
from dashboard.pages.mt5_accounts_page import MT5AccountsPage
from dashboard.pages.telegram_accounts_page import TelegramAccountsPage
from dashboard.pages.channels_page import ChannelsPage
from dashboard.pages.symbols_page import SymbolsPage
from dashboard.pages.settings_page import SettingsPage
from dashboard.pages.logs_page import LogsPage
from dashboard.pages.signal_inspector_page import SignalInspectorPage
from dashboard.pages.trade_timeline_page import TradeTimelinePage
from dashboard.pages.market_data_page import MarketDataPage
from dashboard.pages.live_readiness_page import LiveReadinessPage
from dashboard.pages.paper_trading_page import PaperTradingPage
from dashboard.pages.trading_calendar_page import TradingCalendarPage
from dashboard.event_handlers import DashboardEventHandlers
from dashboard.dialogs.about_dialog import AboutDialog
from utils.application_lifecycle import shutdown_application
from version import APPLICATION_NAME, VERSION
from core.config_service import load_active_config, get_execution_mode
from database.database_manager import database_manager
from repositories.settings_repository import settings_repository
from engine.kraken_engine import kraken_engine
from utils.live_readiness import live_mode_issues


class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(APPLICATION_NAME)

        self.resize(1700, 1000)

        self.build_ui()

    def build_ui(self):

        self.build_toolbar()

        self.build_statusbar()
                
        self.build_central()

        self.build_console()

        self.build_notifications()
        
        self.connect_signals()

        self.initialize_state()

        self.event_handlers = DashboardEventHandlers(self)

    def closeEvent(self, event):
        self.event_handlers.disconnect()
        shutdown_application()
        event.accept()


    def build_toolbar(self):

        self.toolbar = QToolBar()

        self.toolbar.setMovable(False)

        self.toolbar.setIconSize(
            QSize(24, 24)
        )

        self.addToolBar(self.toolbar)

        self.actStart = QAction("Iniciar", self)

        self.actStop = QAction("Detener", self)

        self.actSimulation = QAction("Simulación", self)

        self.actLive = QAction("LIVE", self)

        self.actRefresh = QAction("Actualizar", self)

        self.actSettings = QAction("Configuración", self)

        self.actBackup = QAction("Backup", self)

        self.actRestore = QAction("Restaurar", self)

        self.actAbout = QAction("Acerca de", self)

        self.toolbar.addAction(self.actStart)

        self.toolbar.addAction(self.actStop)

        self.toolbar.addSeparator()

        self.toolbar.addAction(self.actSimulation)

        self.toolbar.addAction(self.actLive)

        self.toolbar.addSeparator()

        self.toolbar.addAction(self.actRefresh)

        self.toolbar.addSeparator()

        self.toolbar.addAction(self.actBackup)

        self.toolbar.addAction(self.actRestore)

        self.toolbar.addSeparator()

        self.toolbar.addAction(self.actSettings)

        self.toolbar.addAction(self.actAbout)

    def build_statusbar(self):

        self.status = QStatusBar()

        self.setStatusBar(self.status)

        self.lblMode = QLabel("OFF")

        self.lblTelegram = QLabel("Telegram: OFFLINE")

        self.lblMT5 = QLabel("MT5: OFFLINE")

        self.lblProfiles = QLabel("Perfiles: 0")

        self.lblAccounts = QLabel("MT5: 0")

        self.lblSignals = QLabel("Señales: 0")

        self.lblOperations = QLabel("Operaciones: 0")

        self.lblProfit = QLabel("Profit: 0")

        self.lblVersion = QLabel(f"Versión {VERSION}")

        self.status.addPermanentWidget(self.lblMode)

        self.status.addPermanentWidget(self.lblTelegram)

        self.status.addPermanentWidget(self.lblMT5)

        self.status.addPermanentWidget(self.lblProfiles)

        self.status.addPermanentWidget(self.lblAccounts)

        self.status.addPermanentWidget(self.lblSignals)

        self.status.addPermanentWidget(self.lblOperations)

        self.status.addPermanentWidget(self.lblProfit)

        self.status.addPermanentWidget(self.lblVersion)

    def build_central(self):

        central = QWidget()

        self.setCentralWidget(central)

        layout = QHBoxLayout(central)

        splitter = QSplitter()

        layout.addWidget(splitter)

        self.menu = QListWidget()

        self.menu.setMaximumWidth(240)

        pages = [

            "Dashboard",

            "Operaciones",

            "Estadísticas",

            "Perfiles",

            "MT5",

            "Telegram",

            "Canales",

            "Símbolos",

            "Logs",

            "Inspector de señales",

            "Línea de tiempo",

            "Datos de mercado",

            "Certificación LIVE",

            "Paper Trading",

            "Calendario de Trading",

            "Configuración"

        ]

        for page in pages:

            self.menu.addItem(
                QListWidgetItem(page)
            )

        splitter.addWidget(self.menu)

        self.stack = QStackedWidget()

        splitter.addWidget(self.stack)

        splitter.setStretchFactor(1, 1)

        self.dashboardPage = DashboardPage()

        self.operationsPage = OperationsPage()

        self.statisticsPage = StatisticsPage()

        self.profilesPage = ProfilesPage()

        self.mt5Page = MT5AccountsPage()

        self.telegramPage = TelegramAccountsPage()

        self.channelsPage = ChannelsPage()

        self.symbolsPage = SymbolsPage()

        self.logsPage = LogsPage()

        self.signalInspectorPage = SignalInspectorPage()

        self.tradeTimelinePage = TradeTimelinePage()

        self.marketDataPage = MarketDataPage()

        self.liveReadinessPage = LiveReadinessPage()

        self.paperTradingPage = PaperTradingPage()

        self.tradingCalendarPage = TradingCalendarPage()

        self.settingsPage = SettingsPage()

        self.stack.addWidget(self.dashboardPage)

        self.stack.addWidget(self.operationsPage)

        self.stack.addWidget(self.statisticsPage)

        self.stack.addWidget(self.profilesPage)

        self.stack.addWidget(self.mt5Page)

        self.stack.addWidget(self.telegramPage)

        self.stack.addWidget(self.channelsPage)

        self.stack.addWidget(self.symbolsPage)

        self.stack.addWidget(self.logsPage)

        self.stack.addWidget(self.signalInspectorPage)

        self.stack.addWidget(self.tradeTimelinePage)

        self.stack.addWidget(self.marketDataPage)

        self.stack.addWidget(self.liveReadinessPage)

        self.stack.addWidget(self.paperTradingPage)

        self.stack.addWidget(self.tradingCalendarPage)

        self.stack.addWidget(self.settingsPage)

        self.menu.currentRowChanged.connect(
            self.stack.setCurrentIndex
        )

        self.menu.setCurrentRow(0)

    def build_console(self):

        self.consoleDock = QDockWidget(
            "Consola"
        )

        self.consoleDock.setObjectName(
            "ConsoleDock"
        )

        self.console = QTextEdit()

        self.console.setReadOnly(True)

        self.consoleDock.setWidget(
            self.console
        )

        self.addDockWidget(

            Qt.BottomDockWidgetArea,

            self.consoleDock

        )

    def build_notifications(self):

        self.notificationDock = QDockWidget(
            "Notificaciones"
        )

        self.notificationDock.setObjectName(
            "NotificationsDock"
        )

        self.notifications = QTextEdit()

        self.notifications.setReadOnly(True)

        self.notificationDock.setWidget(
            self.notifications
        )

        self.addDockWidget(

            Qt.RightDockWidgetArea,

            self.notificationDock

        )

    def connect_signals(self):

        self.actStart.triggered.connect(
            self.start_engine
        )

        self.actStop.triggered.connect(
            self.stop_engine
        )

        self.actSimulation.triggered.connect(
            lambda: self.set_mode("SIMULATION")
        )

        self.actLive.triggered.connect(self.enable_live_mode)

        self.actRefresh.triggered.connect(
            self.refresh_all
        )

        self.actSettings.triggered.connect(
            self.open_settings
        )

        self.actBackup.triggered.connect(
            self.backup_database
        )

        self.actRestore.triggered.connect(
            self.restore_database
        )

        self.actAbout.triggered.connect(self.show_about)

    def show_about(self):
        AboutDialog(self).exec()

    def initialize_state(self):

        self.mode = "OFF"

        self.telegram_online = False

        self.mt5_online = False

        self.active_profiles = 0

        self.mt5_accounts = 0

        self.signal_count = 0

        self.operation_count = 0

        self.total_profit = 0

        self.update_statusbar()

    def update_statusbar(self):

        self.lblMode.setText(

            f"Modo: {self.mode}"

        )

        self.lblTelegram.setText(

            "Telegram: ONLINE"

            if self.telegram_online

            else "Telegram: OFFLINE"

        )

        self.lblMT5.setText(

            "MT5: ONLINE"

            if self.mt5_online

            else "MT5: OFFLINE"

        )

        self.lblProfiles.setText(

            f"Perfiles: {self.active_profiles}"

        )

        self.lblAccounts.setText(

            f"MT5: {self.mt5_accounts}"

        )

        self.lblSignals.setText(

            f"Señales: {self.signal_count}"

        )

        self.lblOperations.setText(

            f"Operaciones: {self.operation_count}"

        )

        self.lblProfit.setText(

            f"Profit: {self.total_profit:.2f}"

        )

    def set_mode(self, mode):

        self.mode = mode

        self.log(

            f"Modo cambiado a {mode}"

        )

        self.update_statusbar()

    def set_telegram_status(self, online):

        self.telegram_online = online

        self.update_statusbar()

        self.notify(

            "Telegram conectado"

            if online

            else "Telegram desconectado"

        )

    def set_mt5_status(self, online):

        self.mt5_online = online

        self.update_statusbar()

        self.notify(

            "MT5 conectado"

            if online

            else "MT5 desconectado"

        )

    def set_profile_count(self, count):

        self.active_profiles = count

        self.update_statusbar()

    def set_account_count(self, count):

        self.mt5_accounts = count

        self.update_statusbar()

    def increment_signal(self):

        self.signal_count += 1

        self.update_statusbar()

    def increment_operation(self):

        self.operation_count += 1

        self.update_statusbar()

    def update_profit(self, value):

        self.total_profit = value

        self.update_statusbar()

    def log(self, text):

        self.console.append(text)

    def notify(self, text):

        self.notifications.append(text)

    def start_engine(self):
        if not load_active_config():
            QMessageBox.warning(self, "Kraken Engine", "No hay un perfil activo. Active un perfil antes de iniciar el motor.")
            return
        if get_execution_mode() == "LIVE":
            issues = live_mode_issues()
            if issues:
                QMessageBox.warning(
                    self,
                    "LIVE bloqueado",
                    "No se puede iniciar LIVE:\n\n- " + "\n- ".join(issues),
                )
                return
        try:
            kraken_engine.start()
            self.set_mode(get_execution_mode())
            self.log("Kraken Engine iniciado.")
        except Exception as error:
            self.log(f"Error al iniciar Kraken Engine: {error}")
            QMessageBox.critical(self, "Kraken Engine", f"No se pudo iniciar el motor: {error}")

    def stop_engine(self):
        try:
            kraken_engine.stop()
            self.set_mode("OFF")
            self.log("Kraken Engine detenido.")
        except Exception as error:
            self.log(f"Error al detener Kraken Engine: {error}")
            QMessageBox.critical(self, "Kraken Engine", f"No se pudo detener el motor: {error}")

    def enable_live_mode(self):
        if not load_active_config():
            QMessageBox.warning(self, "LIVE bloqueado", "No hay un perfil activo.")
            return
        issues = live_mode_issues()
        if issues:
            QMessageBox.warning(
                self,
                "LIVE bloqueado",
                "Complete la preparación de conectividad:\n\n- " + "\n- ".join(issues),
            )
            return
        self.set_mode("LIVE")

    def refresh_all(self):
        try:
            load_active_config()
            for page in (self.dashboardPage, self.operationsPage, self.statisticsPage,
                         self.profilesPage, self.mt5Page, self.telegramPage,
                         self.channelsPage, self.symbolsPage, self.logsPage,
                         self.signalInspectorPage, self.tradeTimelinePage,
                         self.marketDataPage, self.liveReadinessPage, self.paperTradingPage, self.tradingCalendarPage, self.settingsPage):
                refresh = getattr(page, "refresh", None)
                if callable(refresh):
                    refresh()
            self.log("Dashboard actualizado.")
            self.notify("Datos actualizados.")
        except Exception as error:
            self.log(f"Error al actualizar el dashboard: {error}")
            QMessageBox.critical(self, "Actualizar", f"No se pudieron actualizar los datos: {error}")

    def open_settings(self):

        self.stack.setCurrentWidget(

            self.settingsPage

        )

    def backup_database(self):
        suggested_name = f"kraken-{datetime.now():%Y%m%d-%H%M%S}.db"
        destination, _ = QFileDialog.getSaveFileName(
            self, "Guardar respaldo", str(database_manager.database.parent / suggested_name),
            "Base de datos SQLite (*.db)",
        )
        if not destination:
            return
        try:
            database_manager.commit()
            database_manager.backup(Path(destination))
            settings_repository.set("last_backup_path", str(Path(destination).resolve()))
            self.log(f"Respaldo creado: {destination}")
            self.notify("Respaldo de base de datos creado.")
        except OSError as error:
            self.log(f"Error al crear respaldo: {error}")
            QMessageBox.critical(self, "Respaldo", f"No se pudo crear el respaldo: {error}")

    def restore_database(self):
        source, _ = QFileDialog.getOpenFileName(
            self, "Restaurar respaldo", str(database_manager.database.parent),
            "Base de datos SQLite (*.db)",
        )
        if not source:
            return
        if Path(source).resolve() == database_manager.database.resolve():
            QMessageBox.warning(self, "Restaurar", "Seleccione un respaldo distinto a la base activa.")
            return
        if QMessageBox.question(
            self, "Restaurar respaldo",
            "La base de datos activa será reemplazada. ¿Desea continuar?",
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        try:
            kraken_engine.stop()
            database_manager.close()
            shutil.copy2(Path(source), database_manager.database)
            database_manager.initialize()
            self.refresh_all()
            self.log(f"Base de datos restaurada desde: {source}")
            self.notify("Base de datos restaurada correctamente.")
        except (OSError, ValueError) as error:
            self.log(f"Error al restaurar respaldo: {error}")
            QMessageBox.critical(self, "Restaurar", f"No se pudo restaurar la base de datos: {error}")
        return

        self.notify(

            "Restauración iniciada."

        )



