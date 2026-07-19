from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
)

from repositories.mt5_account_repository import mt5_account_repository
from mt5.connector import mt5_connector


class MT5AccountsPage(QWidget):

    def __init__(self):

        super().__init__()

        self.build_ui()

        self.refresh()

    # ======================================================

    def build_ui(self):

        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()

        layout.addLayout(toolbar)

        self.btn_new = QPushButton("Nueva")

        self.btn_edit = QPushButton("Editar")

        self.btn_delete = QPushButton("Eliminar")

        self.btn_test = QPushButton("Probar conexión")

        self.btn_refresh = QPushButton("Actualizar")

        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(self.btn_test)

        toolbar.addStretch()

        toolbar.addWidget(self.btn_refresh)

        self.table = QTableWidget()

        layout.addWidget(self.table)

        self.table.setColumnCount(13)

        self.table.setHorizontalHeaderLabels([

            "ID",
            "Nombre",
            "Broker",
            "Login",
            "Servidor",
            "Estado",
            "Balance",
            "Equity",
            "Magic",
            "Comentario",
            "Desviación",
            "Lote",
            "Activo",

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

        self.btn_refresh.clicked.connect(
            self.refresh
        )

        self.btn_test.clicked.connect(
            self.test_connection
        )

    # ======================================================

    def refresh(self):

        accounts = mt5_account_repository.get_all()

        self.table.setRowCount(len(accounts))

        for row, account in enumerate(accounts):

            values = [

                account.id,
                account.name,
                account.broker,
                account.login,
                account.server,
                "🟢" if account.enabled else "🔴",
                f"{getattr(account,'balance',0):,.2f}",
                f"{getattr(account,'equity',0):,.2f}",
                account.magic_number,
                account.comment,
                account.deviation,
                account.fixed_lot,
                "Sí" if account.enabled else "No",

            ]

            for column, value in enumerate(values):

                item = QTableWidgetItem(str(value))

                item.setTextAlignment(Qt.AlignCenter)

                self.table.setItem(
                    row,
                    column,
                    item,
                )

    # ======================================================

    def selected_account(self):

        row = self.table.currentRow()

        if row < 0:

            return None

        account_id = int(
            self.table.item(row, 0).text()
        )

        return mt5_account_repository.get_by_id(
            account_id
        )

    # ======================================================

    def test_connection(self):

        account = self.selected_account()

        if account is None:

            QMessageBox.warning(
                self,
                "MT5",
                "Seleccione una cuenta."
            )

            return

        connected = mt5_connector.login(account)

        if connected:

            info = mt5_connector.account_info()

            if info:

                account.balance = info.balance
                account.equity = info.equity

            QMessageBox.information(

                self,

                "MT5",

                (
                    "Conexión exitosa\n\n"
                    f"Balance : {account.balance:.2f}\n"
                    f"Equity : {account.equity:.2f}"
                ),

            )

        else:

            QMessageBox.critical(

                self,

                "MT5",

                "No fue posible conectar con la cuenta.",

            )

        self.refresh()