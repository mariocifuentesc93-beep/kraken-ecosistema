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

from repositories.telegram_account_repository import (
    telegram_account_repository,
)

from telegram.account_manager import telegram_account_manager


class TelegramAccountsPage(QWidget):

    def __init__(self):

        super().__init__()

        self.build_ui()

        self.refresh()

    # =====================================================

    def build_ui(self):

        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()

        layout.addLayout(toolbar)

        self.btn_new = QPushButton("Nueva")

        self.btn_edit = QPushButton("Editar")

        self.btn_delete = QPushButton("Eliminar")

        self.btn_login = QPushButton("Iniciar sesión")

        self.btn_logout = QPushButton("Cerrar sesión")

        self.btn_refresh = QPushButton("Actualizar")

        toolbar.addWidget(self.btn_new)

        toolbar.addWidget(self.btn_edit)

        toolbar.addWidget(self.btn_delete)

        toolbar.addWidget(self.btn_login)

        toolbar.addWidget(self.btn_logout)

        toolbar.addStretch()

        toolbar.addWidget(self.btn_refresh)

        self.table = QTableWidget()

        layout.addWidget(self.table)

        self.table.setColumnCount(8)

        self.table.setHorizontalHeaderLabels([

            "ID",
            "Nombre",
            "Teléfono",
            "API ID",
            "Sesión",
            "Estado",
            "Autenticado",
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

        self.btn_login.clicked.connect(
            self.login
        )

        self.btn_logout.clicked.connect(
            self.logout
        )

    # =====================================================

    def refresh(self):

        accounts = telegram_account_repository.get_all()

        self.table.setRowCount(len(accounts))

        for row, account in enumerate(accounts):

            values = [

                account.id,

                account.name,

                account.phone,

                account.api_id,

                account.session_name,

                "🟢" if account.enabled else "🔴",

                "Sí" if getattr(
                    account,
                    "authenticated",
                    False,
                ) else "No",

                "Sí" if account.enabled else "No",

            ]

            for column, value in enumerate(values):

                item = QTableWidgetItem(str(value))

                item.setTextAlignment(
                    Qt.AlignCenter
                )

                self.table.setItem(
                    row,
                    column,
                    item,
                )

    # =====================================================

    def selected_account(self):

        row = self.table.currentRow()

        if row < 0:

            return None

        account_id = int(
            self.table.item(row, 0).text()
        )

        return telegram_account_repository.get_by_id(
            account_id
        )

    # =====================================================

    def login(self):

        account = self.selected_account()

        if account is None:

            QMessageBox.warning(

                self,

                "Telegram",

                "Seleccione una cuenta.",

            )

            return

        try:

            telegram_account_manager.login(account)

            QMessageBox.information(

                self,

                "Telegram",

                "Inicio de sesión exitoso.",

            )

        except Exception as e:

            QMessageBox.critical(

                self,

                "Telegram",

                str(e),

            )

        self.refresh()

    # =====================================================

    def logout(self):

        account = self.selected_account()

        if account is None:

            QMessageBox.warning(

                self,

                "Telegram",

                "Seleccione una cuenta.",

            )

            return

        try:

            telegram_account_manager.logout(account)

            QMessageBox.information(

                self,

                "Telegram",

                "Sesión cerrada.",

            )

        except Exception as e:

            QMessageBox.critical(

                self,

                "Telegram",

                str(e),

            )

        self.refresh()