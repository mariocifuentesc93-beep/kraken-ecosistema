from core.event_bus import event_bus
from core.config_service import get_execution_mode


class DashboardEventHandlers:

    def __init__(self, window):

        self.window = window

        self.connect()

    # =====================================================
    # CONEXIONES
    # =====================================================

    def connect(self):

        # -----------------------------------------------
        # Aplicación
        # -----------------------------------------------

        event_bus.applicationStarted.connect(

            self.on_application_started

        )

        event_bus.applicationStopped.connect(

            self.on_application_stopped

        )

        # -----------------------------------------------
        # Telegram
        # -----------------------------------------------

        event_bus.telegramConnected.connect(

            self.on_telegram_connected

        )

        event_bus.telegramDisconnected.connect(

            self.on_telegram_disconnected

        )

        # -----------------------------------------------
        # MT5
        # -----------------------------------------------

        event_bus.mt5Connected.connect(

            self.on_mt5_connected

        )

        event_bus.mt5Disconnected.connect(

            self.on_mt5_disconnected

        )

        # -----------------------------------------------
        # Señales
        # -----------------------------------------------

        event_bus.signalReceived.connect(

            self.on_signal_received

        )

        # -----------------------------------------------
        # Operaciones
        # -----------------------------------------------

        event_bus.operationCreated.connect(

            self.on_operation_created

        )

        event_bus.operationOpened.connect(

            self.on_operation_opened

        )

        event_bus.operationModified.connect(

            self.on_operation_modified

        )

        event_bus.operationClosed.connect(

            self.on_operation_closed

        )

        # -----------------------------------------------
        # Estadísticas
        # -----------------------------------------------

        event_bus.profitUpdated.connect(

            self.on_profit_updated

        )

        event_bus.statisticsUpdated.connect(

            self.on_statistics_updated

        )

        # -----------------------------------------------
        # Dashboard
        # -----------------------------------------------

        event_bus.dashboardRefreshRequested.connect(

            self.on_dashboard_refresh

        )

        # -----------------------------------------------
        # Logs
        # -----------------------------------------------

        event_bus.logGenerated.connect(

            self.on_log

        )

        event_bus.notificationGenerated.connect(

            self.on_notification

        )

        event_bus.warningGenerated.connect(

            self.on_warning

        )

        event_bus.errorGenerated.connect(

            self.on_error

        )

    # =====================================================
    # APPLICATION
    # =====================================================

    def on_application_started(self, event):

        self.window.log("Kraken Engine iniciado")

        self.window.set_mode(get_execution_mode())

    def on_application_stopped(self, event):

        self.window.log("Kraken Engine detenido")

        self.window.set_mode("OFF")

    # =====================================================
    # TELEGRAM
    # =====================================================

    def on_telegram_connected(self, event):

        self.window.set_telegram_status(True)

    def on_telegram_disconnected(self, event):

        self.window.set_telegram_status(False)

    # =====================================================
    # MT5
    # =====================================================

    def on_mt5_connected(self, event):

        self.window.set_mt5_status(True)

    def on_mt5_disconnected(self, event):

        self.window.set_mt5_status(False)

    # =====================================================
    # SIGNALS
    # =====================================================

    def on_signal_received(self, event):

        self.window.increment_signal()

    # =====================================================
    # OPERACIONES
    # =====================================================

    def on_operation_created(self, event):

        self.window.increment_operation()

    def on_operation_opened(self, event):

        self.window.log("Operación abierta")

    def on_operation_modified(self, event):

        pass

    def on_operation_closed(self, event):

        self.window.log("Operación cerrada")

    # =====================================================
    # PROFIT
    # =====================================================

    def on_profit_updated(self, event):
        value = float(getattr(event, "profit", event))

        self.window.update_profit(value)

    def on_statistics_updated(self, event):

        if hasattr(self.window.statisticsPage, "refresh"):

            self.window.statisticsPage.refresh()

    # =====================================================
    # DASHBOARD
    # =====================================================

    def on_dashboard_refresh(self):

        if hasattr(self.window.dashboardPage, "refresh"):

            self.window.dashboardPage.refresh()

        if hasattr(self.window.operationsPage, "refresh"):

            self.window.operationsPage.refresh()

    # =====================================================
    # LOGS
    # =====================================================

    def on_log(self, text):

        self.window.log(text)

    def on_notification(self, text):

        self.window.notify(text)

    def on_warning(self, text):

        self.window.notify(f"⚠ {text}")

    def on_error(self, text):

        self.window.notify(f"❌ {text}")
