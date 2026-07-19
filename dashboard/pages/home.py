from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)

from dashboard.widgets.metric_card import MetricCard
from dashboard.widgets.status_card import StatusCard
from dashboard.widgets.info_card import InfoCard
from dashboard.widgets.quick_actions import QuickActions


class HomePage(QWidget):

    def __init__(self):

        super().__init__()

        self.build_ui()

    # ---------------------------------------------------------

    def build_ui(self):

        main = QVBoxLayout(self)

        main.setContentsMargins(15, 15, 15, 15)

        main.setSpacing(15)

        # =====================================================
        # MÉTRICAS
        # =====================================================

        metrics = QHBoxLayout()

        self.balance = MetricCard(
            title="Balance",
            value="$0.00",
            subtitle="Cuenta principal",
            icon="💰",
        )

        self.equity = MetricCard(
            title="Equity",
            value="$0.00",
            subtitle="Tiempo real",
            icon="📈",
        )

        self.profit = MetricCard(
            title="Profit",
            value="$0.00",
            subtitle="Hoy",
            icon="💵",
        )

        self.winrate = MetricCard(
            title="Win Rate",
            value="0 %",
            subtitle="Últimos 30 días",
            icon="🎯",
        )

        metrics.addWidget(self.balance)
        metrics.addWidget(self.equity)
        metrics.addWidget(self.profit)
        metrics.addWidget(self.winrate)

        main.addLayout(metrics)

        # =====================================================
        # ESTADOS
        # =====================================================

        status = QHBoxLayout()

        self.telegram = StatusCard("Telegram", "offline")
        self.mt5 = StatusCard("MT5", "offline")
        self.engine = StatusCard("Engine", "offline")
        self.trading = StatusCard("Trading", "offline")
        self.risk = StatusCard("Riesgo", "online")

        status.addWidget(self.telegram)
        status.addWidget(self.mt5)
        status.addWidget(self.engine)
        status.addWidget(self.trading)
        status.addWidget(self.risk)

        main.addLayout(status)

        # =====================================================
        # PANEL CENTRAL
        # =====================================================

        center = QHBoxLayout()

        self.activity = InfoCard(
            "Actividad reciente",
            "Kraken Bot iniciado.\n\nEsperando conexión..."
        )

        self.summary = InfoCard(
            "Resumen del día",
            (
                "Operaciones: 0\n"
                "Ganadas: 0\n"
                "Perdidas: 0\n"
                "Profit: $0.00"
            )
        )

        self.actions = QuickActions()

        center.addWidget(self.activity, 2)
        center.addWidget(self.summary, 1)
        center.addWidget(self.actions, 1)

        main.addLayout(center)

        main.addStretch()

    # ---------------------------------------------------------

    def set_balance(self, value):

        self.balance.set_value(value)

    def set_equity(self, value):

        self.equity.set_value(value)

    def set_profit(self, value):

        self.profit.set_value(value)

    def set_winrate(self, value):

        self.winrate.set_value(value)

    def set_activity(self, text):

        self.activity.set_text(text)

    def set_summary(self, text):

        self.summary.set_text(text)

    def set_telegram_status(self, status):

        self.telegram.set_status(status)

    def set_mt5_status(self, status):

        self.mt5.set_status(status)

    def set_engine_status(self, status):

        self.engine.set_status(status)

    def set_trading_status(self, status):

        self.trading.set_status(status)

    def set_risk_status(self, status):

        self.risk.set_status(status)