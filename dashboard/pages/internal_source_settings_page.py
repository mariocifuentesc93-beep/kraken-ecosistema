import asyncio

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from dashboard.widgets.section_widget import SectionWidget
from repositories.internal_publication_config_repository import (
    internal_publication_config_repository,
)
from repositories.profile_telegram_repository import (
    profile_telegram_channel_repository,
)
from services.internal_publication_configuration_service import (
    InternalPublicationConfigurationService,
)
from telegram.account_manager import telegram_account_manager
from dashboard.ui_theme import refresh_widget_style


class _AsyncCallWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, callable_):
        super().__init__()
        self._callable = callable_

    def run(self):
        try:
            value = self._callable()
            if asyncio.iscoroutine(value):
                value = asyncio.run(value)
            self.finished.emit(value)
        except Exception as error:
            self.failed.emit(str(error))


class InternalSourceSettingsPage(QWidget):
    """Single global configuration point for Inspector INTERNAL publication."""

    def __init__(
        self,
        config_repository=None,
        account_manager=None,
        destinations_provider=None,
        test_sender=None,
        parent=None,
    ):
        super().__init__(parent)
        self._config_repository = (
            config_repository or internal_publication_config_repository
        )
        self._account_manager = account_manager or telegram_account_manager
        self._destinations_provider = (
            destinations_provider
            or profile_telegram_channel_repository.get_available_channels
        )
        self._test_sender = test_sender or self._send_test_message
        self._uses_default_test_sender = test_sender is None
        self._workers = []
        self._destinations = {}
        self._service = InternalPublicationConfigurationService(
            repository=self._config_repository,
            account_provider=self._account_manager.get_account,
            destinations_provider=self._service_destinations,
        )
        self._build_ui()
        self.load()

    def _service_destinations(self, account_id):
        if (
            hasattr(self, "account_combo")
            and self.account_combo.currentData() == account_id
            and self._destinations
        ):
            return list(self._destinations.values())
        return self._destinations_provider(account_id)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        section = SectionWidget("Internal Signal Source")
        form = QGridLayout()

        self.publish_checkbox = QCheckBox(
            "Publicar señales INTERNAL en Telegram"
        )
        self.account_combo = QComboBox()
        self.destination_combo = QComboBox()
        self.destination_name = QLabel("-")
        self.destination_type = QLabel("-")
        self.chat_id_label = QLabel("-")
        self.account_status_label = QLabel("Desconectado")
        self.destination_status_label = QLabel("-")
        self.test_button = QPushButton("Probar envío")
        self.save_button = QPushButton("Guardar configuración")
        self.reload_button = QPushButton("Recargar")
        self.refresh_destinations_button = QPushButton(
            "Actualizar destinos"
        )

        form.addWidget(self.publish_checkbox, 0, 0, 1, 2)
        for row, (label, widget) in enumerate(
            (
                ("Cuenta Telegram", self.account_combo),
                ("Estado de cuenta", self.account_status_label),
                ("Destino", self.destination_combo),
                ("Nombre", self.destination_name),
                ("Tipo", self.destination_type),
                ("Chat ID", self.chat_id_label),
                ("Estado del destino", self.destination_status_label),
            ),
            start=1,
        ):
            form.addWidget(QLabel(label), row, 0)
            form.addWidget(widget, row, 1)
        form.setColumnStretch(1, 1)
        section.addLayout(form)
        layout.addWidget(section)

        buttons = QHBoxLayout()
        buttons.addWidget(self.refresh_destinations_button)
        buttons.addWidget(self.test_button)
        buttons.addStretch()
        buttons.addWidget(self.reload_button)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)
        layout.addStretch()

        self.publish_checkbox.toggled.connect(self._update_enabled)
        self.account_combo.currentIndexChanged.connect(
            lambda *_: self._load_destinations()
        )
        self.destination_combo.currentIndexChanged.connect(
            self._show_destination
        )
        self.reload_button.clicked.connect(self.load)
        self.refresh_destinations_button.clicked.connect(
            self.refresh_destinations
        )
        self.save_button.clicked.connect(self.save)
        self.test_button.clicked.connect(self.test_send)

    @staticmethod
    def _destination_type(item):
        explicit = str(
            item.get("type") or item.get("entity_type") or ""
        ).strip()
        if explicit:
            return explicit
        return "Canal" if item.get("username") else "Grupo"

    def _accounts(self):
        self._account_manager.reload()
        return self._account_manager.get_accounts()

    @staticmethod
    def _masked_identity(account):
        username = str(getattr(account, "username", "") or "").strip()
        if username:
            return f"@{username}"
        phone = "".join(
            character
            for character in str(getattr(account, "phone", "") or "")
            if character.isdigit()
        )
        return f"***{phone[-4:]}" if phone else ""

    def _connection_state(self, account_id):
        method = getattr(self._account_manager, "connection_state", None)
        if callable(method):
            return method(account_id)
        account = self._account_manager.get_account(account_id)
        return (
            "CONNECTED"
            if getattr(account, "connected", True)
            else "DISCONNECTED"
        )

    def _account_text(self, account):
        identity = self._masked_identity(account)
        state = self._connection_state(account.id)
        state_label = {
            "CONNECTED": "Conectada",
            "CONNECTING": "Conectando",
            "ERROR": "Error",
        }.get(state, "Desconectada")
        suffix = f" · {identity}" if identity else ""
        return f"{account.display_name}{suffix} — {state_label}"

    def _load_accounts(self, selected=None):
        self.account_combo.blockSignals(True)
        self.account_combo.clear()
        self.account_combo.addItem("Seleccione una cuenta", None)
        for account in self._accounts():
            self.account_combo.addItem(
                self._account_text(account),
                account.id,
            )
        index = self.account_combo.findData(selected)
        self.account_combo.setCurrentIndex(max(0, index))
        self.account_combo.blockSignals(False)
        self._show_account_status()

    def _show_account_status(self):
        account_id = self.account_combo.currentData()
        state = self._connection_state(account_id) if account_id else "DISCONNECTED"
        label = {
            "CONNECTED": "Conectado",
            "CONNECTING": "Conectando",
            "ERROR": "Error",
        }.get(state, "Desconectado")
        self.account_status_label.setText(label)
        self.account_status_label.setProperty("connectionState", state)
        refresh_widget_style(self.account_status_label)

    def _load_destinations(self, selected=None):
        account_id = self.account_combo.currentData()
        if selected is None:
            selected = self.destination_combo.currentData()
        self.destination_combo.blockSignals(True)
        self.destination_combo.clear()
        self.destination_combo.addItem("Seleccione un chat o canal", None)
        self._destinations = {}
        if account_id is not None:
            for item in self._destinations_provider(account_id):
                chat_id = int(item["chat_id"])
                title = (
                    item.get("title")
                    or item.get("name")
                    or item.get("username")
                    or str(chat_id)
                )
                destination_type = self._destination_type(item)
                normalized = {
                    **item,
                    "chat_id": chat_id,
                    "title": title,
                    "type": destination_type,
                }
                self._destinations[chat_id] = normalized
                self.destination_combo.addItem(
                    f"{title} · {destination_type} · {chat_id}",
                    chat_id,
                )
        index = self.destination_combo.findData(selected)
        self.destination_combo.setCurrentIndex(max(0, index))
        self.destination_combo.blockSignals(False)
        self._show_destination()
        self._show_account_status()
        self._update_actions()

    def refresh_destinations(self):
        loader = getattr(
            self._account_manager,
            "list_sendable_destinations",
            None,
        )
        account_id = self.account_combo.currentData()
        if callable(loader) and account_id is not None:
            self.refresh_destinations_button.setEnabled(False)
            self._start_worker(
                lambda: loader(account_id),
                self._apply_live_destinations,
                self._destination_error,
            )
            return None
        selected = self.destination_combo.currentData()
        self._load_destinations(selected)
        return self.destination_combo.count() - 1

    def _start_worker(self, callable_, success, failure):
        thread = QThread(self)
        worker = _AsyncCallWorker(callable_)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(success)
        worker.failed.connect(failure)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(
            lambda: self._workers.remove(thread)
            if thread in self._workers
            else None
        )
        self._workers.append(thread)
        thread.start()

    def _apply_live_destinations(self, items):
        selected = self.destination_combo.currentData()
        self.destination_combo.blockSignals(True)
        self.destination_combo.clear()
        self.destination_combo.addItem("Seleccione un chat o canal", None)
        self._destinations = {}
        for item in items:
            chat_id = int(item["chat_id"])
            normalized = {
                **item,
                "chat_id": chat_id,
                "title": item.get("title") or str(chat_id),
                "type": self._destination_type(item),
            }
            self._destinations[chat_id] = normalized
            self.destination_combo.addItem(
                f"{normalized['title']} · {normalized['type']} · {chat_id}",
                chat_id,
            )
        self.destination_combo.setCurrentIndex(
            max(0, self.destination_combo.findData(selected))
        )
        self.destination_combo.blockSignals(False)
        self.refresh_destinations_button.setEnabled(
            self.publish_checkbox.isChecked()
        )
        self._show_destination()

    def _destination_error(self, message):
        self.refresh_destinations_button.setEnabled(
            self.publish_checkbox.isChecked()
        )
        self.destination_status_label.setText(message)
        self.destination_status_label.setProperty(
            "connectionState", "ERROR"
        )
        refresh_widget_style(self.destination_status_label)

    def _show_destination(self, *_):
        item = self._destinations.get(
            self.destination_combo.currentData()
        )
        self.destination_name.setText(item["title"] if item else "-")
        self.destination_type.setText(item["type"] if item else "-")
        self.chat_id_label.setText(
            str(item["chat_id"]) if item else "-"
        )
        self.destination_status_label.setText(
            "Válido" if item else "Seleccione un destino válido"
        )
        self.destination_status_label.setProperty(
            "connectionState", "CONNECTED" if item else "ERROR"
        )
        refresh_widget_style(self.destination_status_label)
        self._update_actions()

    def _update_actions(self):
        enabled = self.publish_checkbox.isChecked()
        account_id = self.account_combo.currentData()
        destination_valid = (
            self.destination_combo.currentData() in self._destinations
        )
        connected = (
            self._connection_state(account_id) == "CONNECTED"
            if account_id is not None
            else False
        )
        self.test_button.setEnabled(
            enabled and connected and destination_valid
        )
        if enabled and account_id is not None and not connected:
            self.test_button.setToolTip(
                "Conecte la cuenta Telegram antes de probar el envío."
            )
        elif enabled and not destination_valid:
            self.test_button.setToolTip(
                "Seleccione un destino válido."
            )
        else:
            self.test_button.setToolTip("")

    def _update_enabled(self, enabled):
        self.account_combo.setEnabled(enabled)
        self.destination_combo.setEnabled(enabled)
        self.refresh_destinations_button.setEnabled(enabled)
        self._update_actions()

    def load(self):
        config = self._service.get()
        self._load_accounts(config.telegram_account_id)
        self._load_destinations(config.telegram_output_chat_id)
        self.publish_checkbox.setChecked(config.enabled)
        self._update_enabled(config.enabled)

    def save(self):
        try:
            self._service.save(
                self.publish_checkbox.isChecked(),
                self.account_combo.currentData(),
                self.destination_combo.currentData(),
            )
        except ValueError as error:
            QMessageBox.warning(self, "Inspector INTERNAL", str(error))
            return False
        QMessageBox.information(
            self,
            "Inspector INTERNAL",
            "Configuración global guardada.",
        )
        return True

    async def _send_test_async(self, account_id, chat_id):
        client = self._account_manager.peek_client(account_id)
        if client is None or not client.is_connected():
            raise RuntimeError("Cuenta desconectada")
        await client.send_message(
            chat_id,
            "Kraken: conexión de publicación verificada.",
        )

    def _send_test_message(self, account_id, chat_id):
        asyncio.run(self._send_test_async(account_id, chat_id))

    def test_send(self):
        account_id = self.account_combo.currentData()
        chat_id = self.destination_combo.currentData()
        try:
            self._service.validate(True, account_id, chat_id)
            if self._connection_state(account_id) != "CONNECTED":
                raise RuntimeError("Cuenta desconectada")
            if chat_id not in self._destinations:
                raise RuntimeError("Destino inválido")
            if self._uses_default_test_sender:
                self.test_button.setEnabled(False)
                self._start_worker(
                    lambda: self._test_sender(account_id, chat_id),
                    self._test_send_ok,
                    self._test_send_error,
                )
                return True
            self._test_sender(account_id, chat_id)
        except Exception as error:
            QMessageBox.critical(
                self,
                "Prueba Telegram",
                f"No se pudo enviar el mensaje de prueba: {error}",
            )
            return False
        QMessageBox.information(
            self,
            "Prueba Telegram",
            "Mensaje de prueba enviado correctamente.",
        )
        return True

    def _test_send_ok(self, _result=None):
        self._update_actions()
        QMessageBox.information(
            self,
            "Prueba Telegram",
            "Mensaje de prueba enviado correctamente.",
        )

    def _test_send_error(self, message):
        self._update_actions()
        QMessageBox.critical(
            self,
            "Prueba Telegram",
            f"No se pudo enviar el mensaje de prueba: {message}",
        )
