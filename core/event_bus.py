from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class EventBus(QObject):
    """
    Bus central de eventos del Kraken Bot.
    """

    # ==========================================================
    # APLICACIÓN
    # ==========================================================

    applicationStarted = Signal(object)
    applicationStopped = Signal(object)

    # ==========================================================
    # TELEGRAM
    # ==========================================================

    telegramConnected = Signal(object)
    telegramDisconnected = Signal(object)
    telegramAccountLoaded = Signal(object)

    # ==========================================================
    # MT5
    # ==========================================================

    mt5Connected = Signal(object)
    mt5Disconnected = Signal(object)
    mt5AccountLoaded = Signal(object)

    # ==========================================================
    # SEÑALES
    # ==========================================================

    signalReceived = Signal(object)
    signalValidated = Signal(object)
    signalRejected = Signal(object)
    signalProcessed = Signal(object)

    # ==========================================================
    # PERFILES
    # ==========================================================

    profileStarted = Signal(object)
    profileFinished = Signal(object)
    profileActivated = Signal(object)
    profileDeactivated = Signal(object)

    # ==========================================================
    # EJECUCIÓN
    # ==========================================================

    executionStarted = Signal(object)
    executionFinished = Signal(object)
    executionFailed = Signal(object, str)

    # ==========================================================
    # OPERACIONES
    # ==========================================================

    operationCreated = Signal(object)
    operationOpened = Signal(object)
    operationModified = Signal(object)
    operationClosed = Signal(object)
    operationDeleted = Signal(object)

    # ==========================================================
    # TP / SL
    # ==========================================================

    tp1Reached = Signal(object)
    tp2Reached = Signal(object)
    tp3Reached = Signal(object)

    stopLossReached = Signal(object)

    breakEvenActivated = Signal(object)
    trailingActivated = Signal(object)

    # ==========================================================
    # RIESGO
    # ==========================================================

    riskRejected = Signal(object)

    drawdownReached = Signal(float)
    dailyLimitReached = Signal(float)
    exposureLimitReached = Signal(float)

    # ==========================================================
    # ESTADÍSTICAS
    # ==========================================================

    statisticsUpdated = Signal(dict)

    profitUpdated = Signal(float)
    equityUpdated = Signal(float)
    balanceUpdated = Signal(float)
    winRateUpdated = Signal(float)

    # ==========================================================
    # DASHBOARD
    # ==========================================================

    dashboardRefreshRequested = Signal()

    # ==========================================================
    # LOGS
    # ==========================================================

    logGenerated = Signal(str)
    notificationGenerated = Signal(str)
    errorGenerated = Signal(str)
    warningGenerated = Signal(str)

    # ==========================================================
    # HELPERS
    # ==========================================================

    def log(self, text: str):

        self.logGenerated.emit(str(text))

    def notify(self, text: str):

        self.notificationGenerated.emit(str(text))

    def error(self, text: str):

        self.errorGenerated.emit(str(text))

    def warning(self, text: str):

        self.warningGenerated.emit(str(text))

    def refresh_dashboard(self):

        self.dashboardRefreshRequested.emit()

    def update_profit(self, value: float):

        self.profitUpdated.emit(float(value))

    def update_balance(self, value: float):

        self.balanceUpdated.emit(float(value))

    def update_equity(self, value: float):

        self.equityUpdated.emit(float(value))

    def update_statistics(self, statistics=None):

        if statistics is None:
            statistics = {}

        self.statisticsUpdated.emit(statistics)


# ==============================================================
# INSTANCIA GLOBAL
# ==============================================================

event_bus = EventBus()
