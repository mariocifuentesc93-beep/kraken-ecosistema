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
)

from repositories.profile_repository import profile_repository
from repositories.daily_statistics_repository import (
    daily_statistics_repository,
)
from repositories.symbol_statistics_repository import (
    symbol_statistics_repository,
)

from core.event_bus import event_bus


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

        profiles = profile_repository.get_all()

        active = None

        for profile in profiles:

            if getattr(profile, "is_active", False):

                active = profile

                break

        if active is None:

            return

        self.lbl_operations.setText(
            str(active.total_operations)
        )

        self.lbl_wins.setText(
            str(active.total_wins)
        )

        self.lbl_losses.setText(
            str(active.total_losses)
        )

        self.lbl_be.setText(
            str(active.total_breakeven)
        )

        self.lbl_profit.setText(
            f"${active.gross_profit:,.2f}"
        )

        self.lbl_loss.setText(
            f"${active.gross_loss:,.2f}"
        )

        self.lbl_net.setText(
            f"${active.total_profit:,.2f}"
        )

        self.lbl_wr.setText(
            f"{active.win_rate:.2f}%"
        )

        self.load_daily(active.id)

        self.load_symbols(active.id)

    # =========================================================

    def load_daily(self, profile_id):

        data = daily_statistics_repository.get_all(
            profile_id
        )

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

    def load_symbols(self, profile_id):

        data = symbol_statistics_repository.get_all(
            profile_id
        )

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