from datetime import datetime
from pathlib import Path
import shutil
import threading

from PySide6.QtCore import (QEasingCurve, Qt, QSize, QSettings, QTimer,
                           QPropertyAnimation, Signal)
from PySide6.QtGui import QAction, QFont, QIcon, QImage, QKeySequence, QPainter, QPainterPath, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
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
    QSizePolicy,
    QFrame,
    QGraphicsOpacityEffect,
)

from dashboard.pages.dashboard_page import DashboardPage
from dashboard.pages.operations_page import OperationsPage
from dashboard.pages.statistics_page import StatisticsPage
from dashboard.pages.profiles_page import ProfilesPage
from dashboard.pages.mt5_accounts_page import MT5AccountsPage
from dashboard.pages.mt5_terminals_page import MT5TerminalsPage
from dashboard.pages.telegram_accounts_page import TelegramAccountsPage
from dashboard.pages.channels_page import ChannelsPage
from dashboard.pages.symbols_page import SymbolsPage
from dashboard.pages.settings_page import SettingsPage
from dashboard.pages.internal_source_settings_page import (
    InternalSourceSettingsPage,
)
from dashboard.pages.logs_page import LogsPage
from dashboard.pages.signal_inspector_page import SignalInspectorPage
from dashboard.pages.trade_timeline_page import TradeTimelinePage
from dashboard.pages.market_data_page import MarketDataPage
from dashboard.pages.live_readiness_page import LiveReadinessPage
from dashboard.pages.trading_calendar_page import TradingCalendarPage
from dashboard.pages.analytics_page import AnalyticsPage
from dashboard.pages.symbol_ranking_page import SymbolRankingPage
from dashboard.pages.operational_monitoring_page import (
    OperationalMonitoringPage,
)
from dashboard.event_handlers import DashboardEventHandlers
from dashboard.dialogs.about_dialog import AboutDialog
from utils.application_lifecycle import shutdown_application
from version import APPLICATION_NAME, VERSION
from core.config_service import (load_active_config, get_execution_mode,
                                 get_mt5_account, get_telegram_account)
from database.database_manager import database_manager
from repositories.settings_repository import settings_repository
from engine.kraken_engine import kraken_engine
from utils.live_readiness import live_mode_issues
from dashboard.ui_theme import (NEGATIVE, POSITIVE, WARNING, application_style,
                                apply_standard_components, apply_terminal_palette,
                                configure_active_tables, refresh_widget_style,
                                status_chip)
from dashboard.branding import application_icon, logo_pixmap
from dashboard.icons import (ICON_SIZE, apply_standard_icons, colored_icon, icon_chip,
                             install_icon_system)
from repositories.profile_repository import profile_repository
from repositories.telegram_account_repository import (
    telegram_account_repository,
)
from services.connectivity_status_service import (
    CONNECTED,
    ConnectivityStatus,
    connectivity_status_service,
)
from dashboard.widgets.enterprise import decorate_enterprise_page
from dashboard.layout_manager import enterprise_layout
from dashboard.professional_forms import professional_forms
from dashboard.navigation import (EnterpriseNavigationDelegate, EnterpriseNavigationList,
                                  FULL_TEXT_ROLE, GROUP_ROLE)


def run_telegram_connection_action(account, manager=None, runner=None):
    """Connect/disconnect Telethon only on Kraken's persistent asyncio loop."""
    if manager is None:
        from telegram.account_manager import telegram_account_manager

        manager = telegram_account_manager
    if runner is None:
        from telegram.async_runner import telegram_async_runner

        runner = telegram_async_runner

    if manager.connection_state(account.id) == "CONNECTED":
        return runner.run(manager.disconnect(account.id))
    return runner.run(manager.connect(account.id))


class ResponsiveStack(QStackedWidget):
    """Let the active page adapt instead of inheriting the widest page minimum."""

    def minimumSizeHint(self):
        return QSize(0, 0)


class EnterpriseToolbar(QToolBar):
    """Keep the shell toolbar contract stable as icon-bearing chips change."""

    def sizeHint(self):
        hint = super().sizeHint()
        hint.setHeight(enterprise_layout.TOOLBAR_HEIGHT)
        return hint

    def minimumSizeHint(self):
        return QSize(0, enterprise_layout.TOOLBAR_HEIGHT)


class MainWindow(QMainWindow):
    connection_finished = Signal(str, bool, str)

    def __init__(self):

        super().__init__()

        self.setWindowTitle(APPLICATION_NAME)
        self.setWindowIcon(application_icon())

        self.resize(1600, 900)
        apply_terminal_palette()
        install_icon_system()
        self.setStyleSheet(application_style())

        self.build_ui()
        apply_standard_icons(self)

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

        self.toolbar = EnterpriseToolbar()
        self.toolbar.setObjectName("CommandStrip")
        self.toolbar.setStyleSheet("QToolBar#CommandStrip { background:#09131D; border:0; border-bottom:1px solid #1E3445; padding:6px 7px 7px 7px; }")

        self.toolbar.setMovable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)

        self.toolbar.setIconSize(
            QSize(14, 14)
        )

        self.addToolBar(self.toolbar)

        self.toolbar_sidebar_spacer = QWidget()
        self.toolbar_sidebar_spacer.setMinimumWidth(0)
        self.toolbar_sidebar_spacer.setMaximumWidth(16777215)
        self.toolbar_sidebar_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar_sidebar_spacer.setStyleSheet("background:transparent; border:0;")
        self.toolbar.addWidget(self.toolbar_sidebar_spacer)

        self.actStart = QAction("Iniciar", self)
        self.actStart.setToolTip(
            "Inicia el motor global. Cada perfil conserva su propio modo de ejecución."
        )

        self.actStop = QAction("Detener", self)
        self.actStop.setToolTip(
            "Paro global de emergencia: detiene señales, ejecución, monitor y clientes conectados."
        )

        self.actSimulation = QAction("Simulación", self)

        self.actLive = QAction("LIVE", self)

        self.actRefresh = QAction("Actualizar", self)

        self.actSettings = QAction("Configuración", self)

        self.actBackup = QAction("Backup", self)

        self.actRestore = QAction("Restaurar", self)

        self.actAbout = QAction("Acerca de", self)

        toolbar_icons = (
            (self.actStart, "play", "#00D47A"), (self.actStop, "square", "#FF4D5E"),
            (self.actSimulation, "chart-spline", "#45A3FF"), (self.actLive, "radio", "#FF4D5E"),
            (self.actRefresh, "refresh-cw", "#C7D2DC"), (self.actSettings, "settings", "#C7D2DC"),
        )
        for action, name, color in toolbar_icons:
            action.setIcon(colored_icon(name, color))

        self.toolbar.addAction(self.actStart)

        self.toolbar.addAction(self.actStop)

        self.toolbar.addAction(self.actSimulation)

        self.toolbar.addAction(self.actLive)

        self.toolbar.addAction(self.actRefresh)

        self.toolbar.addAction(self.actSettings)

        # Apply the shell contract after actions have established their size hints.
        self.toolbar.setMinimumHeight(enterprise_layout.TOOLBAR_HEIGHT)
        self.toolbar.setMaximumHeight(enterprise_layout.TOOLBAR_HEIGHT)


    def build_statusbar(self):

        self.status = QStatusBar()
        self.status.setFixedHeight(enterprise_layout.STATUSBAR_HEIGHT)
        self.status.setStyleSheet("QStatusBar{background:transparent;border:0;} QStatusBar::item{border:0;}")

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

        self.status.addPermanentWidget(self.lblProfiles)

        self.status.addPermanentWidget(self.lblAccounts)

        self.status.addPermanentWidget(self.lblSignals)

        self.status.addPermanentWidget(self.lblOperations)

        self.status.addPermanentWidget(self.lblProfit)

        self.lblPaper = QLabel("Paper: listo")
        self.lblReplay = QLabel("Replay: listo")
        self.lblClock = QLabel()
        self.status.addPermanentWidget(self.lblClock)

        self.status.addPermanentWidget(self.lblVersion)

        footer_base = "font-family:'Bahnschrift','Segoe UI';font-size:9px;font-weight:600;color:#C7D2DC;padding:0 16px;border:0;background:transparent;"
        for widget in (self.lblProfiles, self.lblAccounts, self.lblSignals, self.lblOperations):
            widget.setStyleSheet(footer_base)
        self.lblProfit.setStyleSheet(footer_base + "color:#00C853;")
        self.lblClock.setStyleSheet(footer_base + "color:#EAF1F5;")
        self.lblVersion.setStyleSheet(footer_base + "color:#8D9CAA;")

        self.topStatus = self.toolbar
        self.topProfile = QLabel("Perfil: sin activo")
        self.topMode = QLabel("Modo: OFF")
        self.topMT5 = QLabel("MT5: desconectado")
        self.topTelegram = QLabel("Telegram: desconectado")
        self.topInternal = QLabel("INTERNAL: detenido")
        self.topDatabase = QLabel("SQLite: disponible")
        self.topVersion = QLabel(f"v{VERSION}")
        self.topClock = QLabel()
        chips = (
            (self.topMode, "radio", WARNING),
            (self.topMT5, "activity", NEGATIVE),
            (self.topTelegram, "send", NEGATIVE),
            (self.topInternal, "scan-line", NEGATIVE),
            (self.topDatabase, "database-backup", POSITIVE),
            (self.topVersion, "circle-check", POSITIVE),
            (self.topClock, "history", POSITIVE),
        )
        self.status_icon_chips = []
        for widget, icon_name, color in chips:
            chip = icon_chip(widget, icon_name, color)
            chip.setObjectName("EnterpriseStatusChip")
            chip.setStyleSheet(
                f"QWidget#EnterpriseStatusChip {{ {status_chip(color)} }} "
                "QWidget#EnterpriseStatusChip QLabel { background:transparent; border:0; padding:0; }"
            )
            self.status_icon_chips.append(chip)
            self.topStatus.addWidget(chip)
        self.toolbar_right_margin = QWidget()
        self.toolbar_right_margin.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.toolbar_right_margin.setStyleSheet("background:transparent; border:0;")
        self.topStatus.addWidget(self.toolbar_right_margin)
        self.toolbar.setFixedHeight(enterprise_layout.TOOLBAR_HEIGHT)
        self.clock_timer = QTimer(self); self.clock_timer.timeout.connect(self.update_clock); self.clock_timer.start(1000); self.update_clock()

    def build_central(self):

        central = QWidget()

        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        # Align the sidebar with the floating logo panel at the window edge.
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("SidebarRail")
        sidebar.setFixedWidth(enterprise_layout.SIDEBAR_WIDTH)
        sidebar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        sidebar.setStyleSheet("QWidget#SidebarRail { background:#09131D; border:1px solid #1E3445; border-radius:12px; }")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 8, 8, 6)
        sidebar_layout.setSpacing(4)
        brand = KrakenLogo(Path(__file__).resolve().parent.parent / "assets" / "branding" / "trading_ecosystem_logo.png"); brand.setToolTip("Trading Ecosystem"); brand.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        brand_name = QLabel("TRADING")
        brand_name.setAlignment(Qt.AlignHCenter)
        brand_name.setStyleSheet(
            "font-family:'Bahnschrift SemiBold','Segoe UI Semibold';"
            "font-size:19px;font-weight:600;letter-spacing:1.4px;"
            "color:#F4F7FA;background:transparent;border:none;padding:0;"
        )
        brand_subtitle = QLabel("ECOSYSTEM")
        brand_subtitle.setAlignment(Qt.AlignHCenter)
        brand_subtitle.setStyleSheet(
            "font-family:'Segoe UI Semibold';font-size:10px;font-weight:600;"
            "letter-spacing:3.6px;color:#00E676;background:transparent;"
            "border:none;padding:0 0 7px 0;"
        )
        brand_row = QVBoxLayout(); brand_row.setContentsMargins(0, 0, 0, 0); brand_row.setSpacing(1); brand_row.setAlignment(Qt.AlignHCenter); brand_row.addWidget(brand, alignment=Qt.AlignHCenter); brand_row.addWidget(brand_name, alignment=Qt.AlignHCenter); brand_row.addWidget(brand_subtitle, alignment=Qt.AlignHCenter)
        self.sidebar_brand_widgets = (brand, brand_name, brand_subtitle)
        sidebar_layout.addLayout(brand_row)
        self.sidebar_toggle = QPushButton("‹  Contraer navegación")
        sidebar_layout.addWidget(self.sidebar_toggle)
        self.menu = EnterpriseNavigationList()
        self.menu.setObjectName("EnterpriseNavigation")
        self.menu.setProperty("enterpriseNavigation", True)
        self.menu.setSpacing(0)
        self.menu.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.menu.setItemDelegate(EnterpriseNavigationDelegate(self.menu))
        self.menu.setToolTip("Navegación principal")
        sidebar_layout.addWidget(self.menu)
        self.sidebar = sidebar
        self.sidebar_toggle.clicked.connect(self.toggle_sidebar)

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

            "Calendario de Trading",

            "Analíticas",

            "Configuración",

            "Inspector INTERNAL",

            "Terminales MT5",
            "Centro de monitoreo",
            "Ranking de símbolos",

        ]

        icon_map = ["layout-dashboard", "list-checks", "chart-no-axes-combined", "users",
                    "activity", "send", "radio-tower", "tags", "scroll-text", "search-check",
                    "history", "chart-spline", "circle-check", "calendar-days",
                    "chart-no-axes-combined", "settings", "radio-tower", "activity",
                    "activity", "chart-no-axes-combined"]
        groups = (("OPERATION", range(0, 4)), ("TRADING", (12, 13, 14, 19)),
                  ("MARKET", range(4, 8)), ("ANALYSIS", (18, 9, 10, 11, 8)),
                  ("CONFIGURATION", (16, 17, 15)))
        self.page_items = {}
        self.navigation_groups = {}
        for group, indices in groups:
            header = QListWidgetItem(group)
            header.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            header.setData(Qt.UserRole, -1)
            header.setData(GROUP_ROLE, group)
            header.setData(FULL_TEXT_ROLE, group)
            header.setSizeHint(QSize(0, 38))
            header.setFont(QFont("Segoe UI", 8, QFont.DemiBold))
            header.setForeground(Qt.GlobalColor.lightGray)
            self.menu.addItem(header)
            self.navigation_groups[group] = (header, [])
            for index in indices:
                page = pages[index]; icon = icon_map[index] if index < len(icon_map) else "circle-check"
                item = QListWidgetItem(colored_icon(icon, "#C7D2DC"), page)
                item.setData(Qt.UserRole, index); item.setData(GROUP_ROLE, group); item.setData(FULL_TEXT_ROLE, page); item.setToolTip(page); self.menu.addItem(item); self.page_items[page] = item; self.navigation_groups[group][1].append(item)
            if group == "CONFIGURATION":
                for title, action_code, icon in (("Backup", -2, "database-backup"), ("Restaurar", -3, "folder-open")):
                    action_item = QListWidgetItem(colored_icon(icon, "#C7D2DC"), title)
                    action_item.setData(Qt.UserRole, action_code)
                    action_item.setData(GROUP_ROLE, group)
                    action_item.setData(FULL_TEXT_ROLE, title)
                    action_item.setToolTip(title)
                    self.menu.addItem(action_item)
                    self.navigation_groups[group][1].append(action_item)

        layout.addWidget(sidebar)

        self.stack = ResponsiveStack()

        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.stack, 1)

        self.dashboardPage = DashboardPage()
        self.dashboardPage.connection_action_requested.connect(
            self.toggle_connection
        )
        self.connection_finished.connect(self._connection_finished)

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

        self.tradingCalendarPage = TradingCalendarPage()

        self.analyticsPage = AnalyticsPage()

        self.settingsPage = SettingsPage()

        self.internalSourceSettingsPage = InternalSourceSettingsPage()

        self.mt5TerminalsPage = MT5TerminalsPage()
        self.operationalMonitoringPage = OperationalMonitoringPage()
        self.symbolRankingPage = SymbolRankingPage()
        self.operationalMonitoringPage.openTerminalsRequested.connect(
            lambda: self.navigate_to_page("Terminales MT5")
        )

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

        self.stack.addWidget(self.tradingCalendarPage)

        self.stack.addWidget(self.analyticsPage)

        self.stack.addWidget(self.settingsPage)

        self.stack.addWidget(self.internalSourceSettingsPage)

        self.stack.addWidget(self.mt5TerminalsPage)
        self.stack.addWidget(self.operationalMonitoringPage)
        self.stack.addWidget(self.symbolRankingPage)

        page_details = (
            (self.operationsPage, "Operaciones", "Consulte las operaciones generadas por simulación y paper trading."),
            (self.statisticsPage, "Estadísticas", "Revise el rendimiento consolidado de las operaciones registradas."),
            (self.profilesPage, "Perfiles", "Cree y active un perfil para definir operación y riesgo."),
            (self.mt5Page, "Cuentas MT5", "Agregue una cuenta y ejecute el diagnóstico de conexión."),
            (self.telegramPage, "Cuentas Telegram", "Configure una cuenta y complete su autorización."),
            (self.channelsPage, "Canales", "Asigne canales a un perfil de Telegram para monitorizarlos."),
            (self.symbolsPage, "Símbolos", "Agregue símbolos habilitados al perfil activo."),
            (self.logsPage, "Logs", "Los eventos del sistema aparecerán aquí mientras opera."),
            (self.signalInspectorPage, "Inspector de señales", "Las señales procesadas aparecerán al recibir mensajes."),
            (self.tradeTimelinePage, "Línea de tiempo", "Las transiciones aparecerán al simular operaciones."),
            (self.marketDataPage, "Datos de mercado", "Actualice la vista para consultar precios."),
            (self.liveReadinessPage, "Certificación LIVE", "Valide conectividad, riesgo y protecciones antes de operar en LIVE."),
            (self.tradingCalendarPage, "Calendario de Trading", "Cargue demostración o cierre operaciones para ver rendimiento."),
            (self.analyticsPage, "Analíticas", "Las métricas consolidan operaciones SIMULATION, PAPER, DEMO y LIVE."),
            (self.symbolRankingPage, "Ranking de símbolos", "Clasifique símbolos por TP1, TP2, TP3, Stop Loss y rendimiento."),
            (self.settingsPage, "Configuración", "Ajuste el modo y protecciones antes de iniciar el motor."),
            (
                self.internalSourceSettingsPage,
                "Inspector INTERNAL",
                "Configure una sola cuenta y destino para publicar cada señal INTERNAL.",
            ),
            (
                self.mt5TerminalsPage,
                "Terminales MT5",
                "Administre instalaciones independientes y el terminal Scanner.",
            ),
            (
                self.operationalMonitoringPage,
                "Centro de monitoreo",
                "Observe salud, alertas y trazabilidad sin ejecutar acciones operativas.",
            ),
        )
        page_heading_icons = {
            "Perfiles": "users",
            "Operaciones": "list-checks",
            "Estadísticas": "chart-spline",
            "Cuentas MT5": "activity",
            "Cuentas Telegram": "send",
            "Canales": "radio-tower",
            "Símbolos": "tags",
            "Logs": "scroll-text",
            "Inspector de señales": "search-check",
            "Línea de tiempo": "history",
            "Datos de mercado": "chart-spline",
            "Centro de monitoreo": "activity",
            "Certificación LIVE": "circle-check",
            "Calendario de Trading": "calendar-days",
            "Analíticas": "chart-no-axes-combined",
            "Ranking de símbolos": "chart-no-axes-combined",
            "Configuración": "settings",
            "Inspector INTERNAL": "radio-tower",
        }
        for page, title, guidance in page_details:
            decorate_enterprise_page(
                page,
                title,
                guidance,
                page_heading_icons.get(title, "circle-check"),
            )
        enterprise_layout.configure_page(self.dashboardPage)
        enterprise_layout.configure_page(self.liveReadinessPage)
        apply_standard_components(self.dashboardPage)
        apply_standard_components(self.liveReadinessPage)
        for form_page in (
            self.settingsPage,
            self.internalSourceSettingsPage,
            self.telegramPage,
            self.mt5Page,
            self.profilesPage,
            self.tradingCalendarPage,
            self.analyticsPage,
            self.symbolRankingPage,
        ):
            professional_forms.configure(form_page)

        self.menu.currentRowChanged.connect(self.select_navigation_page)
        self.menu.itemClicked.connect(self._handle_navigation_click)
        self.menu.group_toggle_requested.connect(self.toggle_navigation_group)
        self.navigation_shortcut = QShortcut(QKeySequence("Alt+N"), self)
        self.navigation_shortcut.activated.connect(self.menu.setFocus)
        self._restore_navigation_state()

        self.dashboardPage.navigate_requested.connect(self.navigate_to_page)
        self.dashboardPage.action_requested.connect(self.handle_dashboard_action)
        self.dashboardPage.notifications_requested.connect(self.toggle_notifications)

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
        self.notificationDock.toggleViewAction().setIcon(colored_icon("radio", "#45A3FF"))
        # Notifications are available from the dashboard header, not permanently
        # docked at the right side of the application.
        self.notificationDock.hide()

    def toggle_notifications(self):
        self.notificationDock.setVisible(not self.notificationDock.isVisible())

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

        self.connectivity_timer = QTimer(self)
        self.connectivity_timer.setInterval(2000)
        self.connectivity_timer.timeout.connect(
            self.refresh_connectivity_status
        )
        self.connectivity_timer.start()

        self.account_metrics_timer = QTimer(self)
        self.account_metrics_timer.setInterval(5000)
        self.account_metrics_timer.timeout.connect(
            self.refresh_account_metrics_views
        )
        self.account_metrics_timer.start()

        self.refresh_connectivity_status()
        self.update_statusbar()

    def refresh_account_metrics_views(self):
        """Keep profile-scoped MT5 metrics current without manual refresh."""
        self.dashboardPage.refresh()
        self.profilesPage.refresh()

    def refresh_connectivity_status(self):
        """Refresh real service state on the Qt main thread."""
        mt5_status = connectivity_status_service.get_mt5_status()
        telegram_status = connectivity_status_service.get_telegram_status()
        self.mt5_online = mt5_status.connected
        self.telegram_online = telegram_status.connected
        self.update_statusbar()
        self._render_connectivity_status("MT5", mt5_status)
        self._render_connectivity_status(
            "Telegram",
            telegram_status,
        )
        runtime_status = kraken_engine.get_status()
        if runtime_status is not None:
            state = runtime_status.internal_state.value
            label = {
                "STOPPED": "detenido",
                "STARTING": "iniciando",
                "RUNNING": "activo",
                "STOPPING": "deteniendo",
                "ERROR": "error",
            }.get(state, state.lower())
            color_state = {
                "STOPPED": "DISCONNECTED",
                "STARTING": "CONNECTING",
                "RUNNING": "CONNECTED",
                "STOPPING": "CONNECTING",
                "ERROR": "ERROR",
            }.get(state, "ERROR")
            self.topInternal.setText(f"INTERNAL: {label}")
            self.topInternal.setProperty(
                "connectionState", color_state
            )
            self.topInternal.setToolTip(
                runtime_status.last_error or "Fuente CSV KrakenBMSPInspector"
            )
            refresh_widget_style(self.topInternal)

    def toggle_connection(self, service):
        """Connect or disconnect in a worker, never on Qt's UI thread."""
        if service == "Telegram":
            accounts = telegram_account_repository.get_all()
            if not any(
                account.enabled and account.authorized
                for account in accounts
            ):
                self.telegramPage.refresh()
                self.navigate_to_page("Cuentas Telegram")
                return

        def work():
            try:
                load_active_config()
                if service == "MT5":
                    from services.mt5_connection_registry import (
                        mt5_connection_registry,
                    )
                    from repositories.mt5_account_repository import (
                        mt5_account_repository,
                    )

                    active_workers = [
                        value
                        for value in mt5_connection_registry.status().values()
                        if value["alive"]
                    ]
                    if active_workers:
                        mt5_connection_registry.stop_all()
                    else:
                        accounts = [
                            account
                            for account in mt5_account_repository.get_enabled()
                            if getattr(account, "mt5_terminal_id", None)
                            and getattr(account, "auto_connect", True)
                        ]
                        if not accounts:
                            raise RuntimeError(
                                "No hay cuentas MT5 activas vinculadas a "
                                "terminales administradas."
                            )
                        errors = []
                        for account in accounts:
                            try:
                                mt5_connection_registry.connection_for(
                                    account.id,
                                    account.mt5_terminal_id,
                                )
                            except Exception as error:
                                errors.append(f"{account.name}: {error}")
                        if errors:
                            raise RuntimeError(" | ".join(errors))
                else:
                    from telegram.account_manager import (
                        telegram_account_manager,
                    )
                    account = get_telegram_account()
                    if account is None:
                        raise RuntimeError(
                            "No hay una cuenta Telegram activa."
                        )
                    run_telegram_connection_action(
                        account,
                        manager=telegram_account_manager,
                    )
                self.connection_finished.emit(service, True, "")
            except Exception as error:
                self.connection_finished.emit(
                    service, False, str(error)
                )

        threading.Thread(
            target=work,
            name=f"Kraken{service}Connection",
            daemon=True,
        ).start()

    def _connection_finished(self, service, success, error):
        self.refresh_connectivity_status()
        if service == "MT5" and success:
            self.refresh_account_metrics_views()
        if not success:
            self.log(f"Error de conexión {service}: {error}")

    def _apply_connectivity_status(self, service, snapshot):
        if service == "MT5":
            self.mt5_online = snapshot.connected
        else:
            self.telegram_online = snapshot.connected
        self.update_statusbar()
        self._render_connectivity_status(service, snapshot)

    def _render_connectivity_status(self, service, snapshot):
        label = self.topMT5 if service == "MT5" else self.topTelegram
        label.setText(f"{service}: {snapshot.label.lower()}")
        label.setProperty("connectionState", snapshot.state)
        refresh_widget_style(label)
        label.setToolTip(snapshot.tooltip)
        if service == "MT5":
            self.lblMT5.setText(f"MT5: {snapshot.label.upper()}")
        else:
            self.lblTelegram.setText(
                f"Telegram: {snapshot.label.upper()}"
            )
        self.dashboardPage.set_connectivity_status(service, snapshot)

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
        current = QSettings("KrakenBot", "EnterpriseUI").value(
            "sidebar/collapsed", False, type=bool
        )
        self.set_sidebar_collapsed(not current)

    def set_sidebar_collapsed(self, collapsed, persist=True):
        width = 64 if collapsed else enterprise_layout.SIDEBAR_WIDTH
        self.sidebar.setFixedWidth(width)
        self.sidebar_toggle.setText("›" if collapsed else "‹  Contraer navegación")
        self.sidebar_toggle.setToolTip(
            "Expandir navegación" if collapsed else "Contraer navegación"
        )
        for widget in self.sidebar_brand_widgets:
            widget.setVisible(not collapsed)
        self.menu.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        for row in range(self.menu.count()):
            item = self.menu.item(row)
            if item.data(Qt.UserRole) == -1:
                item.setHidden(collapsed)
            else:
                item.setText("" if collapsed else str(item.data(FULL_TEXT_ROLE) or ""))
        self._apply_group_visibility()
        if persist:
            QSettings("KrakenBot", "EnterpriseUI").setValue("sidebar/collapsed", collapsed)

    def _restore_navigation_state(self):
        settings = QSettings("KrakenBot", "EnterpriseUI")
        for group in self.navigation_groups:
            collapsed = settings.value(f"navigation/groups/{group}", False, type=bool)
            self.navigation_groups[group][0].setData(Qt.UserRole + 3, collapsed)
        self._apply_group_visibility()
        last_page = settings.value("navigation/last_page", "Dashboard", type=str)
        self.menu.setCurrentItem(self.page_items.get(last_page, self.page_items["Dashboard"]))
        self.set_sidebar_collapsed(settings.value("sidebar/collapsed", False, type=bool), persist=False)

    def _apply_group_visibility(self):
        for header, items in self.navigation_groups.values():
            collapsed = bool(header.data(Qt.UserRole + 3))
            for item in items:
                item.setHidden(collapsed)

    def _handle_navigation_click(self, item):
        if item.data(Qt.UserRole) == -1:
            self.toggle_navigation_group(item)

    def toggle_navigation_group(self, header):
        group = header.data(GROUP_ROLE)
        collapsed = not bool(header.data(Qt.UserRole + 3))
        header.setData(Qt.UserRole + 3, collapsed)
        for item in self.navigation_groups[group][1]:
            item.setHidden(collapsed)
        QSettings("KrakenBot", "EnterpriseUI").setValue(
            f"navigation/groups/{group}", collapsed
        )
        self.menu.viewport().update()

    def navigate_to_page(self, title):
        item = self.page_items.get(title)
        if item is not None:
            self.menu.setCurrentItem(item)

    def select_navigation_page(self, row):
        item = self.menu.item(row)
        if item is None:
            return
        index = item.data(Qt.UserRole)
        if index == -2:
            self.backup_database()
            return
        if index == -3:
            self.restore_database()
            return
        if isinstance(index, int) and index >= 0:
            if self.stack.currentIndex() != index:
                page = self.stack.widget(index)
                effect = QGraphicsOpacityEffect(page)
                page.setGraphicsEffect(effect)
                effect.setOpacity(0.0)
                self.stack.setCurrentIndex(index)
                self.page_transition = QPropertyAnimation(effect, b"opacity", self)
                self.page_transition.setDuration(175)
                self.page_transition.setStartValue(0.0)
                self.page_transition.setEndValue(1.0)
                self.page_transition.setEasingCurve(QEasingCurve.OutCubic)
                self.page_transition.finished.connect(lambda current=page: current.setGraphicsEffect(None))
                self.page_transition.start()
            QSettings("KrakenBot", "EnterpriseUI").setValue(
                "navigation/last_page", str(item.data(FULL_TEXT_ROLE) or "Dashboard")
            )

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
        state = CONNECTED if online else "DISCONNECTED"
        self._apply_connectivity_status(
            "Telegram",
            ConnectivityStatus("Telegram", state),
        )

    def set_mt5_status(self, online):
        state = CONNECTED if online else "DISCONNECTED"
        self._apply_connectivity_status(
            "MT5",
            ConnectivityStatus("MT5", state),
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
        load_active_config()
        mode = get_execution_mode() or "OFF"
        try:
            kraken_engine.start()
            if mode == "LIVE":
                issues = live_mode_issues()
                if issues:
                    kraken_engine.stop()
                    self.set_mode("OFF")
                    QMessageBox.warning(
                        self,
                        "LIVE bloqueado",
                        "No se puede iniciar LIVE:\n\n- "
                        + "\n- ".join(issues),
                    )
                    return
            self.set_mode(mode)
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
                         self.marketDataPage, self.liveReadinessPage, self.tradingCalendarPage, self.analyticsPage, self.symbolRankingPage, self.settingsPage):
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
    _pixmap_cache = {}

    def __init__(self, path, parent=None):
        super().__init__(parent)
        cache_key = str(Path(path).resolve())
        if cache_key not in self._pixmap_cache:
            # The source artwork is square but is displayed at only
            # 168x136. Pre-scaling avoids processing the full source image for
            # every window while retaining ample detail for the final render.
            source = QPixmap(cache_key).scaled(
                280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self._pixmap_cache[cache_key] = self._blend_into_sidebar(source)
        self.pixmap_source = self._pixmap_cache[cache_key]
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background:transparent;border:0;")

    def sizeHint(self):
        return QSize(168, 136)

    @staticmethod
    def _blend_into_sidebar(pixmap):
        """Remove the baked-in black canvas and feather the branded artwork edges."""
        image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        width, height = image.width(), image.height()
        feather = max(8, min(width, height) // 12)
        for y in range(height):
            for x in range(width):
                color = image.pixelColor(x, y)
                brightness = max(color.red(), color.green(), color.blue())
                # The source image is a neon mark on near-black.  Convert the canvas
                # to transparency, retaining the low-light detail with a soft ramp.
                if brightness <= 20:
                    alpha = 0
                elif brightness < 64:
                    alpha = int((brightness - 20) * 255 / 44)
                else:
                    alpha = color.alpha()
                edge_distance = min(x, y, width - 1 - x, height - 1 - y)
                alpha = int(alpha * min(1.0, max(0.0, edge_distance / feather)))
                color.setAlpha(alpha)
                image.setPixelColor(x, y, color)
        return QPixmap.fromImage(image)

    def paintEvent(self, event):
        painter=QPainter(self); painter.setRenderHint(QPainter.Antialiasing); clip=QPainterPath(); clip.addRoundedRect(self.rect().adjusted(2,2,-2,-2),20,20); painter.setClipPath(clip); painter.drawPixmap(self.rect(),self.pixmap_source); painter.end()
