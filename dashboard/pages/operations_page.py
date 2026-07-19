from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QComboBox,
    QLineEdit,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)

from repositories.operation_repository import operation_repository

from core.event_bus import event_bus


class OperationsPage(QWidget):

    def __init__(self):

        super().__init__()

        self.build_ui()

        self.connect_events()

        self.refresh()

    # ======================================================

    def connect_events(self):

        event_bus.operationCreated.connect(
            self.refresh
        )

        event_bus.operationOpened.connect(
            self.refresh
        )

        event_bus.operationModified.connect(
            self.refresh
        )

        event_bus.operationClosed.connect(
            self.refresh
        )

        event_bus.dashboardRefreshRequested.connect(
            self.refresh
        )

    # ======================================================

    def build_ui(self):

        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()

        layout.addLayout(toolbar)

        toolbar.addWidget(QLabel("Estado"))

        self.cbo_status = QComboBox()

        self.cbo_status.addItems([
            "Todos",
            "OPEN",
            "RUNNING",
            "CLOSED",
            "CANCELLED",
            "ERROR",
            "SIMULATION",
        ])

        self.cbo_status.currentIndexChanged.connect(
            self.refresh
        )

        toolbar.addWidget(self.cbo_status)

        toolbar.addWidget(QLabel("Buscar"))

        self.txt_search = QLineEdit()

        self.txt_search.textChanged.connect(
            self.refresh
        )

        toolbar.addWidget(self.txt_search)

        self.btn_refresh = QPushButton("Actualizar")

        self.btn_refresh.clicked.connect(
            self.refresh
        )

        toolbar.addWidget(self.btn_refresh)

        toolbar.addStretch()

        self.table = QTableWidget()

        layout.addWidget(self.table)

        self.table.setColumnCount(15)

        self.table.setHorizontalHeaderLabels([

            "ID",
            "Fecha",
            "Perfil",
            "Cuenta",
            "Símbolo",
            "Tipo",
            "Lote",
            "Entrada",
            "SL",
            "TP",
            "Salida",
            "Resultado",
            "Profit",
            "Estado",
            "Ticket",

        ])

        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        self.table.setSelectionBehavior(
            QTableWidget.SelectRows
        )

        self.table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        self.table.setAlternatingRowColors(True)

    # ======================================================

    def refresh(self, *args):

        status = self.cbo_status.currentText()

        search = self.txt_search.text().lower()

        operations = operation_repository.get_all()

        rows = []

        for op in operations:

            if status != "Todos" and op.status != status:
                continue

            if search:

                text = (
                    f"{op.symbol} "
                    f"{op.direction} "
                    f"{op.status} "
                    f"{op.result}"
                ).lower()

                if search not in text:
                    continue

            rows.append(op)

        self.table.setRowCount(len(rows))

        for row, op in enumerate(rows):

            values = [

                getattr(op, "id", ""),
                getattr(op, "opened_at", ""),
                getattr(op, "profile_id", ""),
                getattr(op, "mt5_account_id", ""),
                getattr(op, "symbol", ""),
                getattr(op, "direction", ""),
                getattr(op, "volume", ""),
                getattr(op, "entry_price", ""),
                getattr(op, "stop_loss", ""),
                getattr(op, "take_profit", ""),
                getattr(op, "exit_price", ""),
                getattr(op, "result", ""),
                f"{getattr(op, 'profit', 0):.2f}",
                getattr(op, "status", ""),
                getattr(op, "ticket", ""),

            ]

            for col, value in enumerate(values):

                item = QTableWidgetItem(str(value))

                item.setTextAlignment(
                    Qt.AlignCenter
                )

                self.table.setItem(
                    row,
                    col,
                    item,
                )