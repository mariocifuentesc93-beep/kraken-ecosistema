from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QVBoxLayout,
    QWidget,
)

from repositories.telegram_account_repository import telegram_account_repository
from repositories.telegram_channel_repository import telegram_channel_repository
from services.telegram_channel_sync_service import TelegramChannelSyncService
from telegram.async_runner import telegram_async_runner


class _CatalogSyncWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, service, account_id):
        super().__init__()
        self._service = service
        self._account_id = account_id

    def run(self):
        try:
            result = telegram_async_runner.run(
                self._service.synchronize(self._account_id)
            )
            self.finished.emit(result)
        except Exception as error:
            self.failed.emit(str(error))


class ChannelsPage(QWidget):
    """Account-scoped catalog synchronized from Telegram."""

    def __init__(
        self,
        account_repository=None,
        channel_repository=None,
        sync_service=None,
        parent=None,
    ):
        super().__init__(parent)
        self._accounts = account_repository or telegram_account_repository
        self._channels = channel_repository or telegram_channel_repository
        self._sync_service = sync_service or TelegramChannelSyncService(
            account_repository=self._accounts,
            channel_repository=self._channels,
        )
        self._thread = None
        self._worker = None
        self._build_ui()
        self.refresh_accounts()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Cuenta Telegram"))
        self.account_combo = QComboBox()
        toolbar.addWidget(self.account_combo, 1)
        self.update_button = QPushButton("Actualizar chats")
        self.details_button = QPushButton("Ver detalles")
        self.test_button = QPushButton("Probar acceso")
        self.toggle_button = QPushButton("Activar / Desactivar catálogo")
        self.reload_button = QPushButton("Recargar")
        for button in (
            self.update_button,
            self.details_button,
            self.test_button,
            self.toggle_button,
            self.reload_button,
        ):
            toolbar.addWidget(button)
        layout.addLayout(toolbar)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            [
                "Nombre", "Tipo", "Username", "Chat ID",
                "Puede leer", "Puede enviar", "Estado", "Última sincronización",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        self.account_combo.currentIndexChanged.connect(self.refresh)
        self.update_button.clicked.connect(self.synchronize)
        self.reload_button.clicked.connect(self.refresh)
        self.details_button.clicked.connect(self.show_details)
        self.test_button.clicked.connect(self.show_details)
        self.toggle_button.clicked.connect(self.toggle_enabled)

    def refresh_accounts(self):
        selected = self.account_combo.currentData()
        self.account_combo.blockSignals(True)
        self.account_combo.clear()
        accounts = self._accounts.get_all()
        if not accounts:
            self.account_combo.addItem("(No configurada)", None)
        else:
            self.account_combo.addItem("Seleccione una cuenta", None)
            for account in accounts:
                self.account_combo.addItem(account.display_name, account.id)
        self.account_combo.setCurrentIndex(
            max(0, self.account_combo.findData(selected))
        )
        self.account_combo.blockSignals(False)
        self.refresh()

    def refresh(self, *_):
        account_id = self.account_combo.currentData()
        channels = self._channels.list_by_account(account_id)
        self.table.setRowCount(len(channels))
        for row, channel in enumerate(channels):
            values = [
                channel.name,
                self._type_label(channel.chat_type),
                f"@{channel.username}" if channel.username else "—",
                channel.chat_id,
                "Sí" if channel.can_read else "No",
                "Sí" if channel.can_send else "No",
                (
                    "Activo" if channel.enabled and channel.available
                    else "No disponible" if not channel.available
                    else "Desactivado"
                ),
                channel.last_synced_at or "—",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, channel.id)
                self.table.setItem(row, column, item)
        if account_id is None:
            self.status_label.setText(
                "No hay ninguna cuenta Telegram configurada."
                if self.account_combo.count() == 1
                else "Seleccione una cuenta Telegram."
            )
        elif not channels:
            self.status_label.setText(
                "No se encontraron canales, grupos o chats disponibles."
            )
        else:
            self.status_label.setText(
                f"{len(channels)} chat(s) en el catálogo de esta cuenta."
            )

    @staticmethod
    def _type_label(value):
        return {
            "CANAL": "Canal",
            "GRUPO": "Grupo",
            "SUPERGRUPO": "Supergrupo",
            "PRIVADO": "Chat privado",
        }.get(str(value).upper(), str(value).title())

    def synchronize(self):
        account_id = self.account_combo.currentData()
        if account_id is None:
            QMessageBox.information(
                self, "Canales", "Seleccione una cuenta Telegram."
            )
            return
        account = self._accounts.get_by_id(account_id)
        if account is None or not account.authorized:
            self.status_label.setText(
                "La cuenta está desconectada. Conéctala para actualizar chats."
            )
            return
        if self._thread is not None:
            return
        self.update_button.setEnabled(False)
        self.status_label.setText("Actualizando chats…")
        self._thread = QThread(self)
        self._worker = _CatalogSyncWorker(self._sync_service, account_id)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._sync_finished)
        self._worker.failed.connect(self._sync_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._clear_worker)
        self._thread.start()

    def _sync_finished(self, _channels):
        self.refresh()
        self.status_label.setText("Catálogo actualizado correctamente.")

    def _sync_failed(self, message):
        self.status_label.setText(f"No se pudo actualizar: {message}")

    def _clear_worker(self):
        self.update_button.setEnabled(True)
        self._thread = None
        self._worker = None

    def _selected_channel(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        return self._channels.get_by_id(
            self.table.item(row, 0).data(Qt.UserRole)
        )

    def show_details(self):
        channel = self._selected_channel()
        if channel is None:
            QMessageBox.information(self, "Canales", "Seleccione un chat.")
            return
        QMessageBox.information(
            self,
            "Detalles del chat",
            f"{channel.name}\n{self._type_label(channel.chat_type)}\n"
            f"Chat ID: {channel.chat_id}\n"
            f"Lectura: {'Sí' if channel.can_read else 'No'}\n"
            f"Envío: {'Sí' if channel.can_send else 'No'}",
        )

    def toggle_enabled(self):
        channel = self._selected_channel()
        if channel is None:
            QMessageBox.information(self, "Canales", "Seleccione un chat.")
            return
        self._channels.set_enabled(channel.id, not channel.enabled)
        self.refresh()
