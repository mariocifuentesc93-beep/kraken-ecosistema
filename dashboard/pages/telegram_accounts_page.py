import asyncio
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox,
)

from dashboard.dialogs.telegram_account_dialog import TelegramAccountDialog
from models.telegram_account import TelegramAccount
from repositories.telegram_account_repository import telegram_account_repository
from telegram.account_manager import telegram_account_manager


class TelegramAccountsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.build_ui()
        self.refresh()

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
        for button in (self.btn_new, self.btn_edit, self.btn_delete, self.btn_login, self.btn_logout):
            toolbar.addWidget(button)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Nombre", "Teléfono", "API ID", "Sesión", "Estado", "Autenticado", "Activo"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        self.btn_new.clicked.connect(self.new_account)
        self.btn_edit.clicked.connect(self.edit_account)
        self.btn_delete.clicked.connect(self.delete_account)
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_login.clicked.connect(self.login)
        self.btn_logout.clicked.connect(self.logout)

    def refresh(self):
        telegram_account_manager.reload()
        accounts = telegram_account_repository.get_all()
        self.table.setRowCount(len(accounts))
        for row, account in enumerate(accounts):
            values = [
                account.id, account.name, account.phone, account.api_id, account.session_name,
                "🟢" if account.connected else "🔴", "Sí" if account.authorized else "No",
                "Sí" if account.enabled else "No",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, column, item)

    def selected_account(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        return telegram_account_repository.get_by_id(int(self.table.item(row, 0).text()))

    def _apply_dialog_data(self, account, data):
        account.name = data["name"]
        account.phone = data["phone"]
        account.api_id = int(data["api_id"])
        account.api_hash = data["api_hash"]
        account.session_name = data["session_name"]
        account.enabled = data["enabled"]
        account.auto_connect = data["auto_reconnect"]
        account.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return account

    def new_account(self):
        dialog = TelegramAccountDialog(parent=self)
        if dialog.exec():
            try:
                telegram_account_repository.create(
                    self._apply_dialog_data(TelegramAccount(), dialog.get_account_data())
                )
                self.refresh()
            except (TypeError, ValueError) as error:
                QMessageBox.critical(self, "Telegram", f"No se pudo guardar la cuenta: {error}")

    def edit_account(self):
        account = self.selected_account()
        if account is None:
            QMessageBox.warning(self, "Telegram", "Seleccione una cuenta.")
            return
        dialog = TelegramAccountDialog(account=account, parent=self)
        if dialog.exec():
            try:
                telegram_account_repository.update(self._apply_dialog_data(account, dialog.get_account_data()))
                self.refresh()
            except (TypeError, ValueError) as error:
                QMessageBox.critical(self, "Telegram", f"No se pudo actualizar la cuenta: {error}")

    def delete_account(self):
        account = self.selected_account()
        if account is None:
            QMessageBox.warning(self, "Telegram", "Seleccione una cuenta.")
            return
        if QMessageBox.question(
            self, "Eliminar cuenta", f"¿Desea eliminar '{account.display_name}'?",
            QMessageBox.Yes | QMessageBox.No,
        ) == QMessageBox.Yes:
            telegram_account_manager.clients.pop(account.id, None)
            telegram_account_repository.delete(account.id)
            self.refresh()

    @staticmethod
    def _run(coroutine):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        raise RuntimeError("Telegram no puede conectarse mientras hay un ciclo asíncrono activo.")

    def login(self):
        account = self.selected_account()
        if account is None:
            QMessageBox.warning(self, "Telegram", "Seleccione una cuenta.")
            return
        try:
            client = self._run(telegram_account_manager.connect(account.id))
            if client is None:
                raise RuntimeError("No se pudo crear el cliente de Telegram.")
            account.connected = client.is_connected()
            account.authorized = self._run(client.is_user_authorized())
            account.last_error = ""
            account.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            telegram_account_repository.update(account)
            message = "Cuenta conectada y autenticada." if account.authorized else (
                "Cuenta conectada. Complete la autenticación de Telethon para continuar."
            )
            QMessageBox.information(self, "Telegram", message)
        except Exception as error:
            account.connected = False
            account.authorized = False
            account.last_error = str(error)
            telegram_account_repository.update(account)
            QMessageBox.critical(self, "Telegram", f"No se pudo iniciar sesión: {error}")
        self.refresh()

    def logout(self):
        account = self.selected_account()
        if account is None:
            QMessageBox.warning(self, "Telegram", "Seleccione una cuenta.")
            return
        try:
            self._run(telegram_account_manager.disconnect(account.id))
            account.connected = False
            account.authorized = False
            account.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            telegram_account_repository.update(account)
            QMessageBox.information(self, "Telegram", "Sesión cerrada.")
        except Exception as error:
            account.last_error = str(error)
            telegram_account_repository.update(account)
            QMessageBox.critical(self, "Telegram", f"No se pudo cerrar sesión: {error}")
        self.refresh()
