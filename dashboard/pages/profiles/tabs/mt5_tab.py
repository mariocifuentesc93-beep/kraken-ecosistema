from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QGroupBox,
    QTextEdit,
)

from controllers.mt5_account_controller import mt5_account_controller
from dashboard.mt5.mt5_account_dialog import MT5AccountDialog


class MT5Tab(QWidget):

    def __init__(self):

        super().__init__()

        self.profile = None

        self.build_ui()

    # ---------------------------------------------------------

    def build_ui(self):

        main = QVBoxLayout(self)

        # =====================================================
        # CUENTAS MT5
        # =====================================================

        group = QGroupBox("Cuentas MT5")

        layout = QVBoxLayout(group)

        self.table = QTableWidget()

        self.table.setColumnCount(5)

        self.table.setHorizontalHeaderLabels([

            "Nombre",

            "Login",

            "Servidor",

            "Magic",

            "Estado"

        ])

        layout.addWidget(self.table)

        buttons = QHBoxLayout()

        self.new = QPushButton("➕ Nueva")

        self.edit = QPushButton("✏ Editar")

        self.delete = QPushButton("🗑 Eliminar")

        self.test = QPushButton("🔌 Probar")

        self.refresh = QPushButton("🔄 Actualizar")

        buttons.addWidget(self.new)

        buttons.addWidget(self.edit)

        buttons.addWidget(self.delete)

        buttons.addWidget(self.test)

        buttons.addStretch()

        buttons.addWidget(self.refresh)

        layout.addLayout(buttons)

        main.addWidget(group)

        # =====================================================
        # INFORMACIÓN
        # =====================================================

        info = QGroupBox("Información")

        info_layout = QVBoxLayout(info)

        self.details = QTextEdit()

        self.details.setReadOnly(True)

        info_layout.addWidget(self.details)

        main.addWidget(info)

        # =====================================================

        self.new.clicked.connect(self.new_account)

        self.edit.clicked.connect(self.edit_account)

        self.delete.clicked.connect(self.delete_account)

        self.refresh.clicked.connect(self.reload)

        self.table.itemSelectionChanged.connect(

            self.show_details

        )

    # ---------------------------------------------------------

    def load(self, profile):

        self.profile = profile

        self.reload()

    # ---------------------------------------------------------

    def reload(self):

        self.table.setRowCount(0)

        accounts = mt5_account_controller.get_all()

        self.table.setRowCount(len(accounts))

        for row, account in enumerate(accounts):

            self.table.setItem(

                row,

                0,

                QTableWidgetItem(account.name)

            )

            self.table.setItem(

                row,

                1,

                QTableWidgetItem(str(account.login))

            )

            self.table.setItem(

                row,

                2,

                QTableWidgetItem(account.server)

            )

            self.table.setItem(

                row,

                3,

                QTableWidgetItem(str(account.magic_number))

            )

            self.table.setItem(

                row,

                4,

                QTableWidgetItem(

                    "🟢 Activa" if account.active else "🔴 Inactiva"

                )

            )

            self.table.item(row,0).setData(

                1000,

                account

            )

    # ---------------------------------------------------------

    def selected_account(self):

        row = self.table.currentRow()

        if row < 0:

            return None

        return self.table.item(row,0).data(1000)

    # ---------------------------------------------------------

    def show_details(self):

        account = self.selected_account()

        if account is None:

            self.details.clear()

            return

        self.details.setPlainText(f"""
Nombre.............. {account.name}

Login............... {account.login}

Servidor............ {account.server}

Magic............... {account.magic_number}

Terminal............

{account.terminal_path}

Descripción.........

{account.description}
""")

    # ---------------------------------------------------------

    def new_account(self):

        dialog = MT5AccountDialog(self)

        if not dialog.exec():

            return

        data = dialog.get_data()

        mt5_account_controller.create(**data)

        self.reload()

    # ---------------------------------------------------------

    def edit_account(self):

        account = self.selected_account()

        if account is None:

            return

        dialog = MT5AccountDialog(account,self)

        if not dialog.exec():

            return

        data = dialog.get_data()

        account.name = data["name"]
        account.login = data["login"]
        account.password = data["password"]
        account.server = data["server"]
        account.terminal_path = data["terminal_path"]
        account.magic_number = data["magic_number"]
        account.active = data["active"]
        account.auto_connect = data["auto_connect"]
        account.reconnect = data["reconnect"]
        account.description = data["description"]

        mt5_account_controller.update(account)

        self.reload()

    # ---------------------------------------------------------

    def delete_account(self):

        account = self.selected_account()

        if account is None:

            return

        mt5_account_controller.delete(account.id)

        self.reload()