from datetime import datetime
from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QFileDialog, QInputDialog, QLineEdit, QLabel,
)

from dashboard.dialogs.telegram_account_dialog import TelegramAccountDialog
from dashboard.ui_theme import set_visual_role
from models.telegram_account import TelegramAccount
from repositories.telegram_account_repository import telegram_account_repository
from telegram.account_manager import telegram_account_manager
from services.telegram_diagnostics import telegram_diagnostics
from telegram.async_runner import telegram_async_runner


class TelegramAccountsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.build_ui()
        self.refresh()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(9)
        toolbar = QGridLayout()
        layout.addLayout(toolbar)
        self.btn_new = QPushButton("Nueva")
        self.btn_edit = QPushButton("Editar")
        self.btn_delete = QPushButton("Eliminar")
        self.btn_login = QPushButton("Probar conexión")
        self.btn_start_auth = QPushButton("Iniciar autorización")
        self.btn_verify_auth = QPushButton("Verificar código")
        self.btn_logout = QPushButton("Desconectar")
        self.btn_delete_session = QPushButton("Eliminar sesión local")
        self.btn_export_json = QPushButton("Exportar JSON")
        self.btn_export_text = QPushButton("Exportar TXT")
        self.btn_refresh = QPushButton("Actualizar")
        toolbar_buttons = (self.btn_new, self.btn_edit, self.btn_delete, self.btn_login,
                           self.btn_start_auth, self.btn_verify_auth, self.btn_logout,
                           self.btn_delete_session, self.btn_export_json, self.btn_export_text,
                           self.btn_refresh)
        for index, button in enumerate(toolbar_buttons):
            toolbar.addWidget(button, index // 4, index % 4)
        for column in range(4):
            toolbar.setColumnStretch(column, 1)

        self.summary = QLabel("Sin cuentas Telegram configuradas. Agregue una cuenta e inicie su autorización.")
        self.summary.setWordWrap(True)
        set_visual_role(self.summary, "information")
        layout.addWidget(self.summary)

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
        self.btn_start_auth.clicked.connect(self.start_authorization)
        self.btn_verify_auth.clicked.connect(self.verify_authorization)
        self.btn_logout.clicked.connect(self.logout)
        self.btn_delete_session.clicked.connect(self.delete_local_session)
        self.btn_export_json.clicked.connect(lambda: self.export_diagnostic("json"))
        self.btn_export_text.clicked.connect(lambda: self.export_diagnostic("text"))
        self.last_diagnostic = None

    def refresh(self):
        telegram_account_manager.reload()
        accounts = telegram_account_repository.get_all()
        connected = sum(1 for account in accounts if account.connected)
        authorized = sum(1 for account in accounts if account.authorized)
        if accounts:
            self.summary.setText(
                f"Cuentas configuradas: {len(accounts)} · Conectadas: {connected} · "
                f"Autorizadas: {authorized}."
            )
        else:
            self.summary.setText(
                "No hay ninguna cuenta de Telegram configurada.\n\n"
                "Haz clic en Conectar para agregar una nueva cuenta."
            )
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
        return telegram_async_runner.run(coroutine)

    def login(self):
        account = self.selected_account()
        if account is None:
            QMessageBox.warning(self, "Telegram", "Seleccione una cuenta.")
            return
        try:
            self.last_diagnostic = self._run(telegram_diagnostics.test_connection(account))
            self._show_diagnostic(self.last_diagnostic)
        except Exception as error:
            QMessageBox.critical(self, "Telegram", f"No se pudo ejecutar diagnóstico: {error}")
        self.refresh()

    def start_authorization(self):
        account = self.selected_account()
        if account is None:
            QMessageBox.warning(self, "Telegram", "Seleccione una cuenta.")
            return
        account = self._prepare_authorization_account(account)
        self.btn_start_auth.setEnabled(False)
        self.btn_start_auth.setText("Esperando código…")
        try:
            report = self._run(
                telegram_diagnostics.start_authorization(account)
            )
            if report["status"] == telegram_diagnostics.CODE_REQUIRED:
                report = self._prompt_and_verify(account, report)
            self.last_diagnostic = report
            self._show_diagnostic(report)
        except Exception as error:
            QMessageBox.critical(
                self,
                "Autorización Telegram",
                f"No se pudo completar la autorización: {error}",
            )
        finally:
            self.btn_start_auth.setText("Iniciar autorización")
            self.btn_start_auth.setEnabled(True)
            self.refresh()

    @staticmethod
    def _prepare_authorization_account(account):
        changed = False
        if not str(getattr(account, "session_name", "") or "").strip():
            account.session_name = (
                f"sessions/telegram_{uuid4().hex[:16]}"
            )
            changed = True
        if not bool(getattr(account, "enabled", False)):
            account.enabled = True
            changed = True
        if changed:
            account.updated_at = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            telegram_account_repository.update(account)
            telegram_account_manager.reload()
        return account

    def verify_authorization(self):
        account = self.selected_account()
        if account is None:
            QMessageBox.warning(self, "Telegram", "Seleccione una cuenta.")
            return
        report = self._prompt_and_verify(account)
        if report is None:
            return
        self.last_diagnostic = report
        self._show_diagnostic(report)
        self.refresh()

    def _prompt_and_verify(self, account, current_report=None):
        code, accepted = QInputDialog.getText(
            self,
            "Autorización Telegram",
            "Introduzca el código recibido en Telegram",
        )
        if not accepted or not code:
            return current_report
        code = code.strip()
        if not code:
            return current_report
        report = self._run(telegram_diagnostics.verify_code(account, code))
        if report["status"] == telegram_diagnostics.PASSWORD_REQUIRED:
            password, accepted = QInputDialog.getText(
                self,
                "Verificación en dos pasos",
                "Introduzca la contraseña de dos pasos de Telegram",
                QLineEdit.Password,
            )
            if not accepted or not password:
                return report
            report = self._run(
                telegram_diagnostics.verify_code(
                    account,
                    code,
                    password,
                )
            )
        return report

    def logout(self):
        account = self.selected_account()
        if account is None:
            QMessageBox.warning(self, "Telegram", "Seleccione una cuenta.")
            return
        try:
            self.last_diagnostic = self._run(telegram_diagnostics.disconnect(account))
            self._show_diagnostic(self.last_diagnostic)
        except Exception as error:
            QMessageBox.critical(self, "Telegram", f"No se pudo cerrar sesión: {error}")
        self.refresh()

    def delete_local_session(self):
        account = self.selected_account()
        if account is None:
            QMessageBox.warning(self, "Telegram", "Seleccione una cuenta.")
            return
        if QMessageBox.question(self, "Eliminar sesión", "¿Eliminar el archivo local de sesión?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        self.last_diagnostic = self._run(telegram_diagnostics.delete_local_session(account))
        self._show_diagnostic(self.last_diagnostic)
        self.refresh()

    def export_diagnostic(self, report_type):
        if not self.last_diagnostic:
            QMessageBox.warning(self, "Telegram", "Primero ejecute una prueba de conexión.")
            return
        suffix = "json" if report_type == "json" else "txt"
        path, _ = QFileDialog.getSaveFileName(self, "Exportar diagnóstico", f"telegram_diagnostic.{suffix}")
        if path:
            (telegram_diagnostics.export_json if report_type == "json" else telegram_diagnostics.export_text)(self.last_diagnostic, path)
            QMessageBox.information(self, "Telegram", "Diagnóstico exportado correctamente.")

    def _show_diagnostic(self, report):
        message = (f"Estado: {report['status']}\nConectado: {report['connected']}\n"
                   f"Autorizado: {report['authorized']}\nUsuario: {report['username']}\n"
                   f"Teléfono: {report['phone_masked']}\nCanales: {sum(row['accessible'] for row in report['channels'])}/{len(report['channels'])}\n\n"
                   f"{report['last_error']}")
        if report["success"]:
            QMessageBox.information(self, "Diagnóstico Telegram", message)
        else:
            QMessageBox.warning(self, "Diagnóstico Telegram", message)
