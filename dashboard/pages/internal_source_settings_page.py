import asyncio
from dataclasses import dataclass
import traceback

from PySide6.QtCore import QObject, QThread, Signal, Qt
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
from repositories.log_repository import log_repository
from repositories.telegram_channel_repository import telegram_channel_repository
from services.internal_publication_configuration_service import (
    InternalPublicationConfigurationService,
)
from telegram.account_manager import telegram_account_manager
from telegram.async_runner import telegram_async_runner
from services.telegram_channel_sync_service import TelegramChannelSyncService
from dashboard.ui_theme import refresh_widget_style


class _AsyncCallWorker(QObject):
    completed = Signal(object)

    def __init__(self, callable_):
        super().__init__()
        self._callable = callable_

    def run(self):
        try:
            value = self._callable()
            if asyncio.iscoroutine(value):
                raise RuntimeError(
                    "El worker recibió una coroutine sin programar."
                )
            outcome = _AsyncCallOutcome(value=value)
        except Exception as error:
            outcome = _AsyncCallOutcome(
                failure=_AsyncCallFailure(
                    error,
                    traceback.format_exc(),
                )
            )
        self.completed.emit(outcome)


@dataclass(frozen=True)
class _AsyncCallFailure:
    error: Exception
    traceback_text: str


@dataclass(frozen=True)
class _AsyncCallOutcome:
    value: object = None
    failure: _AsyncCallFailure | None = None


class InternalSourceSettingsPage(QWidget):
    """Single global configuration point for Inspector INTERNAL publication."""

    def __init__(
        self,
        config_repository=None,
        account_manager=None,
        destinations_provider=None,
        test_sender=None,
        async_runner=None,
        event_log=None,
        test_timeout=10.0,
        parent=None,
    ):
        super().__init__(parent)
        self._config_repository = (
            config_repository or internal_publication_config_repository
        )
        self._account_manager = account_manager or telegram_account_manager
        self._uses_catalog_provider = destinations_provider is None
        self._destinations_provider = (
            destinations_provider
            or self._catalog_destinations
        )
        self._sync_service = TelegramChannelSyncService(
            channel_repository=telegram_channel_repository,
            account_manager=self._account_manager,
        )
        self._test_sender = test_sender or self._send_test_message
        self._uses_default_test_sender = test_sender is None
        self._async_runner = async_runner or telegram_async_runner
        self._event_log = event_log or log_repository
        self._test_timeout = test_timeout
        self._test_context = None
        self._workers = []
        self._destinations = {}
        self._service = InternalPublicationConfigurationService(
            repository=self._config_repository,
            account_provider=self._account_manager.get_account,
            destinations_provider=self._service_destinations,
        )
        self._build_ui()
        self.load()

    @staticmethod
    def _catalog_destinations(account_id):
        return [
            {
                **channel.__dict__,
                "title": channel.name,
                "type": channel.chat_type,
            }
            for channel in telegram_channel_repository.list_sendable(account_id)
        ]

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
        section = SectionWidget("PUBLICACIÓN EN TELEGRAM")
        form = QGridLayout()

        self.publish_checkbox = QCheckBox("Habilitado")
        self.account_combo = QComboBox()
        self.destination_combo = QComboBox()
        self.destination_name = QLabel("—")
        self.destination_type = QLabel("—")
        self.chat_id_label = QLabel("—")
        self.account_status_label = QLabel("Desconectado")
        self.destination_status_label = QLabel("Sin configurar")
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
        accounts = self._accounts()
        self.account_combo.addItem(
            "(No configurada)"
            if not accounts
            else "Seleccione una cuenta",
            None,
        )
        for account in accounts:
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
        self.destination_combo.addItem("(No configurado)", None)
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
        account_id = self.account_combo.currentData()
        if account_id is not None and self._uses_catalog_provider:
            self.refresh_destinations_button.setEnabled(False)
            self._start_worker(
                lambda: telegram_async_runner.run(
                    self._sync_service.synchronize(account_id)
                ),
                lambda _items: self._reload_after_sync(),
                self._destination_error,
            )
            return None
        selected = self.destination_combo.currentData()
        self._load_destinations(selected)
        return self.destination_combo.count() - 1

    def _reload_after_sync(self):
        selected = self.destination_combo.currentData()
        self.refresh_destinations_button.setEnabled(
            self.publish_checkbox.isChecked()
        )
        self._load_destinations(selected)

    def _start_worker(self, callable_, success, failure):
        thread = QThread(self)
        worker = _AsyncCallWorker(callable_)
        worker_entry = {
            "thread": thread,
            "worker": worker,
            "success": success,
            "failure": failure,
            "outcome": None,
        }
        worker.moveToThread(thread)
        thread.started.connect(worker.run)

        def capture_outcome(outcome):
            worker_entry["outcome"] = outcome

        worker.completed.connect(
            capture_outcome,
            Qt.DirectConnection,
        )
        worker.completed.connect(worker.deleteLater)
        worker.completed.connect(thread.quit, Qt.DirectConnection)
        thread.finished.connect(
            lambda: self._finish_worker(worker_entry)
        )
        thread.finished.connect(thread.deleteLater)
        # Keep both Qt objects alive until the queued result has been handled.
        self._workers.append(worker_entry)
        thread.start()

    def _finish_worker(self, worker_entry):
        if worker_entry in self._workers:
            self._workers.remove(worker_entry)
        outcome = worker_entry["outcome"]
        if outcome is None:
            worker_entry["failure"](
                _AsyncCallFailure(
                    RuntimeError("El worker terminó sin resultado."),
                    "El QThread finalizó sin emitir completed.",
                )
            )
            return
        if outcome.failure is not None:
            worker_entry["failure"](outcome.failure)
            return
        worker_entry["success"](outcome.value)

    def _apply_live_destinations(self, items):
        selected = self.destination_combo.currentData()
        self.destination_combo.blockSignals(True)
        self.destination_combo.clear()
        self.destination_combo.addItem("(No configurado)", None)
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
        if isinstance(message, _AsyncCallFailure):
            message = str(message.error)
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
        self.destination_name.setText(item["title"] if item else "—")
        self.destination_type.setText(item["type"] if item else "—")
        self.chat_id_label.setText(
            str(item["chat_id"]) if item else "—"
        )
        self.destination_status_label.setText(
            "Válido" if item else "Sin configurar"
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
        return self._async_runner.run(
            self._send_test_async(account_id, chat_id),
            timeout=self._test_timeout,
        )

    def _test_identifiers(self, account_id, chat_id):
        destination = self._destinations.get(chat_id) or {}
        channel_id = destination.get(
            "id",
            destination.get("telegram_channel_id"),
        )
        return {
            "telegram_account_id": account_id,
            "telegram_channel_id": channel_id,
            "chat_id": chat_id,
        }

    @staticmethod
    def _test_log_message(state, identifiers, detail=""):
        message = (
            f"Prueba de publicación Telegram {state}. "
            f"telegram_account_id={identifiers['telegram_account_id']}; "
            f"telegram_channel_id={identifiers['telegram_channel_id']}; "
            f"chat_id={identifiers['chat_id']}"
        )
        return f"{message}; {detail}" if detail else message

    def _log_test(self, level, state, identifiers, detail=""):
        self._event_log.add(
            level,
            "Inspector INTERNAL",
            self._test_log_message(
                state,
                identifiers,
                detail,
            ),
        )

    def test_send(self):
        account_id = self.account_combo.currentData()
        chat_id = self.destination_combo.currentData()
        identifiers = self._test_identifiers(account_id, chat_id)
        self._test_context = identifiers
        self._log_test("INFO", "INICIADA", identifiers)
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
                    lambda result: self._test_send_ok(
                        result,
                        identifiers,
                    ),
                    lambda failure: self._test_send_error(
                        failure,
                        identifiers,
                    ),
                )
                return True
            self._test_sender(account_id, chat_id)
        except Exception as error:
            self._test_send_error(
                _AsyncCallFailure(error, traceback.format_exc()),
                identifiers,
            )
            return False
        self._test_send_ok(None, identifiers)
        return True

    def _test_send_ok(self, _result=None, identifiers=None):
        identifiers = identifiers or self._test_context
        self._test_context = None
        self._update_actions()
        try:
            self._log_test("INFO", "ÉXITO", identifiers)
            QMessageBox.information(
                self,
                "Prueba Telegram",
                "Mensaje de prueba enviado correctamente.",
            )
        except Exception:
            self._log_test(
                "ERROR",
                "ERROR",
                identifiers,
                traceback.format_exc(),
            )
            raise

    def _test_send_error(self, failure, identifiers=None):
        identifiers = identifiers or self._test_context
        if not isinstance(failure, _AsyncCallFailure):
            failure = _AsyncCallFailure(
                RuntimeError(str(failure)),
                str(failure),
            )
        is_timeout = isinstance(failure.error, TimeoutError)
        state = "TIMEOUT" if is_timeout else "ERROR"
        detail = (
            f"{failure.error}\n{failure.traceback_text}".strip()
        )
        self._test_context = None
        self._update_actions()
        try:
            self._log_test("ERROR", state, identifiers, detail)
            if is_timeout:
                QMessageBox.warning(
                    self,
                    "Prueba Telegram",
                    "La prueba de envío agotó el tiempo de espera.",
                )
            else:
                QMessageBox.critical(
                    self,
                    "Prueba Telegram",
                    "No se pudo enviar el mensaje de prueba: "
                    f"{failure.error}",
                )
        except Exception:
            self._log_test(
                "ERROR",
                "ERROR",
                identifiers,
                traceback.format_exc(),
            )
            raise
