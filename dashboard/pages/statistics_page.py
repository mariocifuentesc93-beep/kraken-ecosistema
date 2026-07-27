from datetime import date, datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QGroupBox,
    QGridLayout,
    QHeaderView,
    QComboBox,
    QDateEdit,
    QPushButton,
)

from repositories.profile_repository import profile_repository
from repositories.daily_statistics_repository import (
    daily_statistics_repository,
)
from repositories.symbol_statistics_repository import (
    symbol_statistics_repository,
)

from core.event_bus import event_bus
from services.trading_analytics_service import trading_analytics_service
from services.trading_calendar_service import trading_calendar_service


class StatisticsPage(QWidget):

    def __init__(self):

        super().__init__()

        self.build_ui()

        self.connect_events()

        self.refresh()

    # =========================================================
    # EVENTOS
    # =========================================================

    def connect_events(self):

        event_bus.statisticsUpdated.connect(
            self.refresh
        )

        event_bus.profitUpdated.connect(
            self.refresh
        )

        event_bus.operationCreated.connect(
            self.refresh
        )

        event_bus.operationClosed.connect(
            self.refresh
        )

        event_bus.dashboardRefreshRequested.connect(
            self.refresh
        )

    # =========================================================
    # UI
    # =========================================================

    def build_ui(self):

        layout = QVBoxLayout(self)

        filters = QHBoxLayout()
        self.start = QDateEdit()
        self.end = QDateEdit()
        self.start.setCalendarPopup(True)
        self.end.setCalendarPopup(True)
        self.start.setDate(date(date.today().year, 1, 1))
        self.end.setDate(date.today())
        self.profile = QComboBox()
        self.symbol = QComboBox()
        self.account = QComboBox()
        self.mode = QComboBox()
        self.source = QComboBox()
        self.status = QComboBox()
        self.direction = QComboBox()
        self.result = QComboBox()
        for label, field in (
            ("Desde", self.start), ("Hasta", self.end),
            ("Perfil", self.profile), ("Símbolo", self.symbol),
            ("Cuenta", self.account), ("Modo", self.mode),
            ("Fuente", self.source), ("Estado", self.status),
            ("Dirección", self.direction), ("Resultado", self.result),
        ):
            filters.addWidget(QLabel(label))
            filters.addWidget(field)
        refresh = QPushButton("Actualizar")
        refresh.clicked.connect(self.refresh)
        filters.addWidget(refresh)
        layout.addLayout(filters)

        summary = QGroupBox("Resumen General")

        layout.addWidget(summary)

        grid = QGridLayout(summary)

        self.lbl_operations = QLabel("0")
        self.lbl_wins = QLabel("0")
        self.lbl_losses = QLabel("0")
        self.lbl_be = QLabel("0")
        self.lbl_profit = QLabel("$0.00")
        self.lbl_loss = QLabel("$0.00")
        self.lbl_net = QLabel("$0.00")
        self.lbl_wr = QLabel("0 %")

        widgets = [

            ("Operaciones", self.lbl_operations),
            ("Ganadas", self.lbl_wins),
            ("Perdidas", self.lbl_losses),
            ("Break Even", self.lbl_be),

            ("Profit", self.lbl_profit),
            ("Loss", self.lbl_loss),
            ("Resultado", self.lbl_net),
            ("Win Rate", self.lbl_wr),

        ]

        row = 0
        col = 0

        for text, widget in widgets:

            title = QLabel(text)

            title.setAlignment(Qt.AlignCenter)

            widget.setAlignment(Qt.AlignCenter)

            grid.addWidget(title, row, col)

            grid.addWidget(widget, row + 1, col)

            col += 1

            if col == 4:

                col = 0
                row += 2

        tables = QHBoxLayout()

        layout.addLayout(tables)

        self.daily_table = QTableWidget()

        self.daily_table.setColumnCount(8)

        self.daily_table.setHorizontalHeaderLabels([

            "Fecha",
            "Ops",
            "Wins",
            "Loss",
            "BE",
            "Profit",
            "Net",
            "WR",

        ])

        self.daily_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        tables.addWidget(self.daily_table)

        self.symbol_table = QTableWidget()

        self.symbol_table.setColumnCount(7)

        self.symbol_table.setHorizontalHeaderLabels([

            "Símbolo",
            "Ops",
            "Wins",
            "Loss",
            "Profit",
            "Net",
            "WR",

        ])

        self.symbol_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        tables.addWidget(self.symbol_table)

    # =========================================================

    def refresh(self, *args):
        options = trading_calendar_service.filter_options()
        self._fill(
            self.profile,
            [(name, identifier) for identifier, name in options["profiles"]],
        )
        self._fill(
            self.account,
            [(name, identifier) for identifier, name in options["accounts"]],
        )
        for combo, key in (
            (self.symbol, "symbols"), (self.mode, "modes"),
            (self.source, "sources"), (self.status, "statuses"),
            (self.direction, "directions"), (self.result, "results"),
        ):
            self._fill(combo, [(value, value) for value in options[key]])

        filters = {
            "start": self.start.date().toPython(),
            "end": self.end.date().toPython(),
            "profile": self.profile.currentData(),
            "symbol": self.symbol.currentData(),
            "account": self.account.currentData(),
            "mode": self.mode.currentData(),
            "source": self.source.currentData(),
            "status": self.status.currentData(),
            "direction": self.direction.currentData(),
            "result": self.result.currentData(),
        }
        metrics = trading_analytics_service.metrics(filters)
        self._current_rows = metrics["closed"]

        self.lbl_operations.setText(
            str(metrics["total"])
        )

        self.lbl_wins.setText(
            str(sum(float(row["net"]) > 0 for row in self._current_rows))
        )

        self.lbl_losses.setText(
            str(sum(float(row["net"]) < 0 for row in self._current_rows))
        )

        self.lbl_be.setText(
            str(sum(float(row["net"]) == 0 for row in self._current_rows))
        )

        self.lbl_profit.setText(
            f"${metrics['gross_profit']:,.2f}"
        )

        self.lbl_loss.setText(
            f"${metrics['gross_loss']:,.2f}"
        )

        self.lbl_net.setText(
            f"${metrics['net']:,.2f}"
        )

        self.lbl_wr.setText(
            f"{metrics['win_rate']:.2f}%"
        )

        self.load_daily()

        self.load_symbols()

    @staticmethod
    def _fill(combo, items):
        selected = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Todos", None)
        for label, value in items:
            combo.addItem(str(label), value)
        index = combo.findData(selected)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    # =========================================================

    def load_daily(self):
        grouped = {}
        for row in getattr(self, "_current_rows", []):
            day = str(row["date"])[:10]
            item = grouped.setdefault(
                day, {"operations": 0, "wins": 0, "losses": 0,
                      "breakeven": 0, "gross_profit": 0.0,
                      "net_profit": 0.0}
            )
            value = float(row["net"] or 0)
            item["operations"] += 1
            item["wins"] += value > 0
            item["losses"] += value < 0
            item["breakeven"] += value == 0
            item["gross_profit"] += max(value, 0)
            item["net_profit"] += value
        data = [
            {"statistic_date": day, **values,
             "win_rate": round(values["wins"] / values["operations"] * 100, 2)}
            for day, values in sorted(grouped.items(), reverse=True)
        ]

        self.daily_table.setRowCount(len(data))

        for row, item in enumerate(data):

            values = [

                item["statistic_date"],
                item["operations"],
                item["wins"],
                item["losses"],
                item["breakeven"],
                f"{item['gross_profit']:.2f}",
                f"{item['net_profit']:.2f}",
                f"{item['win_rate']:.2f}%",

            ]

            for col, value in enumerate(values):

                table_item = QTableWidgetItem(str(value))

                table_item.setTextAlignment(Qt.AlignCenter)

                self.daily_table.setItem(
                    row,
                    col,
                    table_item,
                )

    # =========================================================

    def load_symbols(self):
        grouped = {}
        for row in getattr(self, "_current_rows", []):
            item = grouped.setdefault(
                row["symbol"], {"operations": 0, "wins": 0, "losses": 0,
                                "profit": 0.0, "loss": 0.0}
            )
            value = float(row["net"] or 0)
            item["operations"] += 1
            item["wins"] += value > 0
            item["losses"] += value < 0
            item["profit"] += max(value, 0)
            item["loss"] += min(value, 0)
        data = [
            {"symbol": symbol, **values,
             "win_rate": round(values["wins"] / values["operations"] * 100, 2)}
            for symbol, values in sorted(grouped.items())
        ]

        self.symbol_table.setRowCount(len(data))

        for row, item in enumerate(data):

            values = [

                item["symbol"],
                item["operations"],
                item["wins"],
                item["losses"],
                f"{item['profit']:.2f}",
                f"{item['profit'] + item['loss']:.2f}",
                f"{item['win_rate']:.2f}%",

            ]

            for col, value in enumerate(values):

                table_item = QTableWidgetItem(str(value))

                table_item.setTextAlignment(Qt.AlignCenter)

                self.symbol_table.setItem(
                    row,
                    col,
                    table_item,
                )
