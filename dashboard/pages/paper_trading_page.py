from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dashboard.styles import BORDER_COLOR, CARD_COLOR, PRIMARY_COLOR, SECONDARY_TEXT, TEXT_COLOR
from dashboard.widgets.enterprise import StatCard
from dashboard.ui_theme import set_visual_role
from repositories.profile_repository import profile_repository
from trading.paper_trading_engine import paper_trading_engine


class PaperTradingPage(QWidget):
    def __init__(self):
        super().__init__()
        self.build_ui()
        self.refresh()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        top = QHBoxLayout()
        account = QFrame()
        set_visual_role(account, "panel")
        form = QGridLayout(account)
        form.setContentsMargins(12, 10, 12, 10)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(6)
        self.start = QLineEdit()
        self.currency = QLineEdit()
        self.slippage = QLineEdit()
        self.commission = QLineEdit()
        self.fallback = QCheckBox("Permitir precios de respaldo cuando MT5 no esté disponible")
        for row, (label, field) in enumerate((("Saldo inicial", self.start), ("Moneda", self.currency), ("Deslizamiento", self.slippage), ("Comisión", self.commission), ("Mercado", self.fallback))):
            form.addWidget(QLabel(label), row, 0)
            form.addWidget(field, row, 1)
        form.setColumnStretch(1, 1)
        save = QPushButton("Guardar cuenta virtual")
        save.clicked.connect(self.save_settings)
        form.addWidget(save, 5, 1)
        top.addWidget(account, 2)

        summary_box = QFrame()
        set_visual_role(summary_box, "panel")
        summary_layout = QVBoxLayout(summary_box)
        summary_layout.setContentsMargins(12, 10, 12, 10)
        title = QLabel("Resumen de cuenta virtual")
        set_visual_role(title, "panelTitle")
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        set_visual_role(self.summary, "subtitle")
        summary_layout.addWidget(title)
        summary_layout.addWidget(self.summary)
        summary_layout.addStretch()
        top.addWidget(summary_box, 3)
        layout.addLayout(top)

        cards = QHBoxLayout()
        self.balance_card = StatCard("Balance", "$0.00", "Cuenta virtual")
        self.equity_card = StatCard("Equity", "$0.00", "Capital disponible", "#45A3FF")
        self.daily_card = StatCard("P/L diario", "$0.00", "Rendimiento del día")
        self.drawdown_card = StatCard("Drawdown", "0.00%", "Máximo registrado", "#FF4D5A")
        for card in (self.balance_card, self.equity_card, self.daily_card, self.drawdown_card):
            cards.addWidget(card)
        layout.addLayout(cards)

        action_bar = QHBoxLayout()
        action_bar.addStretch()
        refresh = QPushButton("Actualizar")
        refresh.clicked.connect(self.refresh)
        reset = QPushButton("Reiniciar cuenta virtual")
        reset.clicked.connect(self.reset)
        action_bar.addWidget(refresh)
        action_bar.addWidget(reset)
        layout.addLayout(action_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Símbolo", "Dirección", "Estado", "Lote", "P/L neto", "Resultado"]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table, 1)

    def refresh(self):
        profile = profile_repository.get_active()
        if not profile:
            self.summary.setText("Active un perfil para crear y consultar operaciones virtuales.")
            self.table.setRowCount(0)
            return
        data = paper_trading_engine.summary(profile.id)
        account = data["account"]
        self.start.setText(str(account["starting_balance"]))
        self.currency.setText(account["currency"])
        self.slippage.setText(str(account["slippage"]))
        self.commission.setText(str(account["commission"]))
        self.fallback.setChecked(bool(account["allow_fallback"]))
        self.summary.setText(
            f"Perfil: {profile.name}\nAbiertas: {data['open']} · Pendientes: {data['pending']} · "
            f"Cerradas: {data['closed']}\nWin rate: {data['win_rate']}%"
        )
        self.balance_card.set_value(f"{account['balance']:.2f} {account['currency']}")
        self.equity_card.set_value(f"{account['equity']:.2f} {account['currency']}")
        self.daily_card.set_value(f"{data['daily_pl']:.2f}")
        self.drawdown_card.set_value(f"{data['drawdown']:.2f}%")
        self.table.setRowCount(len(data["trades"]))
        for row, trade in enumerate(data["trades"]):
            values = (
                trade["id"], trade["symbol"], trade["direction"], trade["status"],
                trade["volume"], trade["net_pl"], trade["metadata"].get("result", ""),
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))

    def reset(self):
        profile = profile_repository.get_active()
        if profile and QMessageBox.question(
            self, "Paper trading", "¿Reiniciar la cuenta virtual y eliminar sus operaciones?",
            QMessageBox.Yes | QMessageBox.No,
        ) == QMessageBox.Yes:
            paper_trading_engine.reset(profile.id)
            self.refresh()

    def save_settings(self):
        profile = profile_repository.get_active()
        if not profile:
            return
        try:
            paper_trading_engine.configure(
                profile.id,
                starting_balance=float(self.start.text()),
                currency=self.currency.text() or "USD",
                slippage=float(self.slippage.text()),
                commission=float(self.commission.text()),
                allow_fallback=self.fallback.isChecked(),
            )
            self.refresh()
        except ValueError:
            QMessageBox.warning(self, "Paper trading", "Revise los valores de la cuenta virtual.")
