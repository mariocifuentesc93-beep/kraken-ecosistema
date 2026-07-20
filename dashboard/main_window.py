from datetime import datetime
from pathlib import Path
import shutil

from PySide6.QtCore import Qt, QSize, QSettings, QTimer
from PySide6.QtGui import QAction, QIcon, QPainter, QPainterPath, QPixmap
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
    QStyle,
    QPushButton,
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
from dashboard.pages.analytics_page import AnalyticsPage
from dashboard.pages.replay_page import ReplayPage
from dashboard.event_handlers import DashboardEventHandlers
from dashboard.dialogs.about_dialog import AboutDialog
from utils.application_lifecycle import shutdown_application
from version import APPLICATION_NAME, VERSION
from core.config_service import load_active_config, get_execution_mode
from database.database_manager import database_manager
from repositories.settings_repository import settings_repository
from engine.kraken_engine import kraken_engine
from utils.live_readiness import live_mode_issues
from dashboard.ui_theme import (NEGATIVE, POSITIVE, WARNING, application_style,
                                apply_terminal_palette, configure_active_tables, status_chip)
from dashboard.branding import application_icon, logo_pixmap
from repositories.profile_repository import profile_repository
from dashboard.widgets.enterprise import decorate_enterprise_page


class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(APPLICATION_NAME)
        self.setWindowIcon(application_icon())

        self.resize(1600, 900)
        apply_terminal_palette()
        self.setStyleSheet(application_style())

        self.build_ui()

    def build_ui(self):

        self.build_toolbar()

        self.build_statusbar()
                
        self.build_central()
        configure_active_tables(self)

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
            QSize(16, 16)
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

        toolbar_icons = (
            (self.actStart, QStyle.SP_MediaPlay), (self.actStop, QStyle.SP_MediaStop),
            (self.actSimulation, QStyle.SP_ComputerIcon), (self.actLive, QStyle.SP_BrowserStop),
            (self.actRefresh, QStyle.SP_BrowserReload), (self.actBackup, QStyle.SP_DialogSaveButton),
            (self.actRestore, QStyle.SP_DialogOpenButton), (self.actSettings, QStyle.SP_FileDialogDetailedView),
            (self.actAbout, QStyle.SP_MessageBoxInformation),
        )
        for action, icon in toolbar_icons:
            action.setIcon(self.style().standardIcon(icon))

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

        self.lblPaper = QLabel("Paper: listo")
        self.lblReplay = QLabel("Replay: listo")
        self.lblClock = QLabel()
        self.status.addPermanentWidget(self.lblPaper)
        self.status.addPermanentWidget(self.lblReplay)
        self.status.addPermanentWidget(self.lblClock)

        self.status.addPermanentWidget(self.lblVersion)

        self.topStatus = QToolBar("Estado", self)
        self.topStatus.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, self.topStatus)
        self.topProfile = QLabel("Perfil: sin activo")
        self.topMode = QLabel("Modo: OFF")
        self.topMT5 = QLabel("MT5: desconectado")
        self.topTelegram = QLabel("Telegram: desconectado")
        self.topDatabase = QLabel("SQLite: disponible")
        self.topVersion = QLabel(f"v{VERSION}")
        self.topClock = QLabel()
        for widget, color in ((self.topProfile, WARNING), (self.topMode, WARNING), (self.topMT5, NEGATIVE), (self.topTelegram, NEGATIVE), (self.topDatabase, POSITIVE), (self.topVersion, POSITIVE)):
            widget.setStyleSheet(status_chip(color)); self.topStatus.addWidget(widget)
        self.topClock.setStyleSheet(status_chip(POSITIVE)); self.topStatus.addWidget(self.topClock)
        self.clock_timer = QTimer(self); self.clock_timer.timeout.connect(self.update_clock); self.clock_timer.start(1000); self.update_clock()

    def build_central(self):

        central = QWidget()

        self.setCentralWidget(central)

        layout = QHBoxLayout(central)

        splitter = QSplitter()

        layout.addWidget(splitter)

        sidebar = QWidget()
        sidebar.setMinimumWidth(185)
        sidebar.setMaximumWidth(200)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 14, 10, 10)
        brand = KrakenLogo(Path(__file__).resolve().parent.parent / "assets" / "branding" / "kraken_enterprise.png"); brand.setToolTip("Kraken Bot Enterprise")
        brand_name = QLabel("KRAKEN BOT\nENTERPRISE")
        brand_name.setStyleSheet("font-size:18px;font-weight:800;color:#00C853;padding:8px;")
        brand_row = QVBoxLayout(); brand_row.setContentsMargins(0, 0, 0, 0); brand_row.addWidget(brand, alignment=Qt.AlignCenter); brand_row.addWidget(brand_name, alignment=Qt.AlignCenter)
        section = QLabel("OPERACIÓN  ·  DATOS  ·  SISTEMA")
        section.setStyleSheet("color:#B0BEC5;font-size:10px;padding:0 8px 6px 8px;")
        sidebar_layout.addLayout(brand_row)
        sidebar_layout.addWidget(section)
        self.sidebar_toggle = QPushButton("‹  Contraer navegación")
        sidebar_layout.addWidget(self.sidebar_toggle)
        self.menu = QListWidget()
        self.menu.setToolTip("Navegación principal")
        sidebar_layout.addWidget(self.menu)
        self.sidebar = sidebar
        self.sidebar_toggle.clicked.connect(self.toggle_sidebar)
        if QSettings("KrakenBot", "EnterpriseUI").value("sidebar/collapsed", False, type=bool):
            self.toggle_sidebar()

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

            "Analíticas",

            "Replay",

            "Configuración"

        ]

        icon_map = [QStyle.SP_ComputerIcon, QStyle.SP_FileDialogDetailedView, QStyle.SP_DesktopIcon,
                    QStyle.SP_DirHomeIcon, QStyle.SP_DriveHDIcon, QStyle.SP_DialogYesButton,
                    QStyle.SP_DirIcon, QStyle.SP_FileDialogContentsView, QStyle.SP_MessageBoxInformation,
                    QStyle.SP_FileDialogInfoView, QStyle.SP_BrowserReload, QStyle.SP_DriveNetIcon,
                    QStyle.SP_MessageBoxWarning, QStyle.SP_MediaPlay, QStyle.SP_FileDialogListView,
                    QStyle.SP_FileDialogDetailedView, QStyle.SP_FileDialogContentsView]
        for index, page in enumerate(pages):
            icon = icon_map[index] if index < len(icon_map) else QStyle.SP_MediaSeekForward
            item = QListWidgetItem(self.style().standardIcon(icon), page)
            item.setToolTip(page)
            self.menu.addItem(item)

        splitter.addWidget(sidebar)

        self.stack = QStackedWidget()

        splitter.addWidget(self.stack)

        splitter.setStretchFactor(1, 1)
        splitter.setSizes([192, 1200])

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

        self.analyticsPage = AnalyticsPage()

        self.replayPage = ReplayPage()

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

        self.stack.addWidget(self.analyticsPage)

        self.stack.addWidget(self.replayPage)

        self.stack.addWidget(self.settingsPage)

        page_details = (
            (self.profilesPage, "Perfiles", "Cree y active un perfil para definir operación y riesgo."),
            (self.mt5Page, "Cuentas MT5", "Agregue una cuenta y ejecute el diagnóstico de conexión."),
            (self.telegramPage, "Cuentas Telegram", "Configure una cuenta y complete su autorización."),
            (self.channelsPage, "Canales", "Asigne canales a un perfil de Telegram para monitorizarlos."),
            (self.symbolsPage, "Símbolos", "Agregue símbolos habilitados al perfil activo."),
            (self.logsPage, "Logs", "Los eventos del sistema aparecerán aquí mientras opera."),
            (self.signalInspectorPage, "Inspector de señales", "Las señales procesadas aparecerán al recibir mensajes."),
            (self.tradeTimelinePage, "Línea de tiempo", "Las transiciones aparecerán al simular operaciones."),
            (self.marketDataPage, "Datos de mercado", "Actualice la vista para consultar precios."),
            (self.paperTradingPage, "Paper Trading", "Simule señales para crear posiciones virtuales."),
            (self.tradingCalendarPage, "Calendario de Trading", "Cargue demostración o cierre operaciones para ver rendimiento."),
            (self.analyticsPage, "Analíticas", "Las métricas se generan con operaciones simuladas o paper trading."),
            (self.replayPage, "Replay", "Seleccione una fecha con operaciones para reproducir su línea de tiempo."),
            (self.settingsPage, "Configuración", "Ajuste el modo y protecciones antes de iniciar el motor."),
        )
        for page, title, guidance in page_details:
            decorate_enterprise_page(page, title, guidance)

        self.menu.currentRowChanged.connect(self.stack.setCurrentIndex)

        self.menu.setCurrentRow(0)

        self.dashboardPage.navigate_requested.connect(self.navigate_to_page)
        self.dashboardPage.action_requested.connect(self.handle_dashboard_action)

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
        self.consoleDock.hide()
        view_menu = self.menuBar().addMenu("Ver")
        view_menu.addAction(self.consoleDock.toggleViewAction())
        self.consoleDock.visibilityChanged.connect(lambda visible: QSettings("KrakenBot", "EnterpriseUI").setValue("docks/console_visible", visible))
        self.consoleDock.setVisible(QSettings("KrakenBot", "EnterpriseUI").value("docks/console_visible", False, type=bool))

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
        active = profile_repository.get_active()
        self.topProfile.setText(f"Perfil: {active.name if active else 'sin activo'}")
        self.topMode.setText(f"Modo: {self.mode}")
        self.topMT5.setText("MT5: conectado" if self.mt5_online else "MT5: desconectado")
        self.topTelegram.setText("Telegram: conectado" if self.telegram_online else "Telegram: desconectado")
        self.topDatabase.setText("SQLite: disponible" if database_manager.table_exists("profiles") else "SQLite: error")

    def update_clock(self):
        current = datetime.now().strftime("%H:%M:%S")
        self.lblClock.setText(current)
        self.topClock.setText(current)

    def toggle_sidebar(self):
        collapsed = not self.menu.isHidden()
        self.menu.setVisible(not collapsed)
        self.sidebar.setMaximumWidth(78 if collapsed else 200)
        self.sidebar.setMinimumWidth(72 if collapsed else 185)
        self.sidebar_toggle.setText("›  Expandir navegación" if collapsed else "‹  Contraer navegación")
        QSettings("KrakenBot", "EnterpriseUI").setValue("sidebar/collapsed", collapsed)

    def navigate_to_page(self, title):
        for row in range(self.menu.count()):
            if self.menu.item(row).text() == title:
                self.menu.setCurrentRow(row)
                return

    def handle_dashboard_action(self, action):
        if action == "SIMULATION":
            self.set_mode("SIMULATION")

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
                         self.marketDataPage, self.liveReadinessPage, self.paperTradingPage, self.tradingCalendarPage, self.analyticsPage, self.replayPage, self.settingsPage):
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



class KrakenLogo(QLabel):
    def __init__(self, path, parent=None):
        super().__init__(parent); self.pixmap_source=QPixmap(str(path)); self.setFixedSize(130,106); self.setStyleSheet("background:transparent;border:0;")
    def paintEvent(self, event):
        painter=QPainter(self); painter.setRenderHint(QPainter.Antialiasing); clip=QPainterPath(); clip.addRoundedRect(self.rect().adjusted(3,3,-3,-3),18,18); painter.setClipPath(clip); painter.drawPixmap(self.rect(),self.pixmap_source); painter.end()
