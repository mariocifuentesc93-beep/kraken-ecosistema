import os
import time
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from dashboard.pages.internal_source_settings_page import (
    InternalSourceSettingsPage,
)
from models.internal_publication_config import InternalPublicationConfig


class MemoryConfigRepository:
    def __init__(self):
        self.config = InternalPublicationConfig()

    def get(self):
        return self.config

    def save(self, config):
        self.config = config
        return config


class MemoryLogRepository:
    def __init__(self):
        self.rows = []

    def add(self, level, module, message):
        self.rows.append(
            {
                "level": level,
                "module": module,
                "message": message,
            }
        )
        return len(self.rows)


class FakeAccountManager:
    def __init__(self, connected=True):
        self.connected = connected
        self.account = SimpleNamespace(
            id=7,
            display_name="Cuenta Kraken",
            enabled=True,
            connected=connected,
            username="kraken",
            phone="+573001234567",
        )

    def reload(self):
        return True

    def get_accounts(self):
        return [self.account]

    def get_account(self, account_id):
        return self.account if account_id == 7 else None

    def connection_state(self, account_id=None):
        return "CONNECTED" if self.connected else "DISCONNECTED"


class EmptyAccountManager:
    def reload(self):
        return True

    def get_accounts(self):
        return []

    def get_account(self, account_id):
        return None

    def connection_state(self, account_id=None):
        return "DISCONNECTED"


def destinations(account_id):
    if account_id != 7:
        return []
    return [
        {
            "id": 42,
            "title": "Señales Premium",
            "type": "Canal",
            "chat_id": -1001234567890,
        }
    ]


def test_global_internal_settings_are_not_profile_fields():
    app = QApplication.instance() or QApplication([])
    repository = MemoryConfigRepository()
    manager = FakeAccountManager()
    sent = []
    page = InternalSourceSettingsPage(
        config_repository=repository,
        account_manager=manager,
        destinations_provider=destinations,
        test_sender=lambda account, chat: sent.append((account, chat)),
    )
    page.show()
    app.processEvents()

    page.publish_checkbox.setChecked(True)
    page.account_combo.setCurrentIndex(page.account_combo.findData(7))
    page.destination_combo.setCurrentIndex(
        page.destination_combo.findData(-1001234567890)
    )

    assert page.destination_name.text() == "Señales Premium"
    assert page.destination_type.text() == "Canal"
    assert page.chat_id_label.text() == "-1001234567890"
    assert page._service.save(
        True,
        page.account_combo.currentData(),
        page.destination_combo.currentData(),
    ) == InternalPublicationConfig(
        enabled=True,
        telegram_account_id=7,
        telegram_output_chat_id=-1001234567890,
        destination_name="Señales Premium",
        destination_type="Canal",
    )
    page._test_sender(7, -1001234567890)
    assert sent == [(7, -1001234567890)]
    page.close()


def test_clean_installation_shows_empty_internal_publication_state():
    app = QApplication.instance() or QApplication([])
    page = InternalSourceSettingsPage(
        config_repository=MemoryConfigRepository(),
        account_manager=EmptyAccountManager(),
        destinations_provider=lambda _account_id: [],
        test_sender=lambda *_: pytest.fail("No debe enviar"),
    )
    page.show()
    app.processEvents()

    assert page.publish_checkbox.isChecked() is False
    assert page.account_combo.currentText() == "(No configurada)"
    assert page.account_combo.currentData() is None
    assert page.destination_combo.currentText() == "(No configurado)"
    assert page.destination_combo.currentData() is None
    assert page.chat_id_label.text() == "—"
    assert page.destination_name.text() == "—"
    assert page.destination_type.text() == "—"
    assert page.test_button.isEnabled() is False
    page.close()


def test_test_send_validates_without_saving_configuration(monkeypatch):
    app = QApplication.instance() or QApplication([])
    repository = MemoryConfigRepository()
    manager = FakeAccountManager()
    sent = []
    events = MemoryLogRepository()
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)
    page = InternalSourceSettingsPage(
        config_repository=repository,
        account_manager=manager,
        destinations_provider=destinations,
        test_sender=lambda account, chat: sent.append((account, chat)),
        event_log=events,
    )
    page.publish_checkbox.setChecked(True)
    page.account_combo.setCurrentIndex(page.account_combo.findData(7))
    page.destination_combo.setCurrentIndex(
        page.destination_combo.findData(-1001234567890)
    )

    assert page.test_send() is True
    assert repository.config == InternalPublicationConfig()
    assert sent == [(7, -1001234567890)]
    assert "INICIADA" in events.rows[0]["message"]
    assert "ÉXITO" in events.rows[-1]["message"]
    page.close()


def test_disconnected_account_blocks_test_send(monkeypatch):
    app = QApplication.instance() or QApplication([])
    repository = MemoryConfigRepository()
    manager = FakeAccountManager(connected=False)
    errors = []
    events = MemoryLogRepository()
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda *args: errors.append(args[-1]),
    )
    page = InternalSourceSettingsPage(
        config_repository=repository,
        account_manager=manager,
        destinations_provider=destinations,
        test_sender=lambda *_: pytest.fail("No debe enviar"),
        event_log=events,
    )
    page.publish_checkbox.setChecked(True)
    page.account_combo.setCurrentIndex(page.account_combo.findData(7))
    page.destination_combo.setCurrentIndex(
        page.destination_combo.findData(-1001234567890)
    )

    assert page.test_button.isEnabled() is False
    assert page.test_send() is False
    assert "Cuenta desconectada" in errors[-1]
    assert "ERROR" in events.rows[-1]["message"]
    page.close()


class ChatWriteForbiddenError(Exception):
    pass


class PeerIdInvalidError(Exception):
    pass


@pytest.mark.parametrize(
    ("raised", "expected_state"),
    [
        (ChatWriteForbiddenError("ChatWriteForbidden"), "ERROR"),
        (PeerIdInvalidError("PeerIdInvalid"), "ERROR"),
        (TimeoutError("send timed out"), "TIMEOUT"),
        (RuntimeError("future failed"), "ERROR"),
    ],
)
def test_test_send_failures_are_visible_logged_and_reenable_button(
    monkeypatch,
    raised,
    expected_state,
):
    app = QApplication.instance() or QApplication([])
    events = MemoryLogRepository()
    dialogs = []
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda *args: dialogs.append(("critical", args[-1])),
    )
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda *args: dialogs.append(("warning", args[-1])),
    )

    def sender(*_):
        raise raised

    page = InternalSourceSettingsPage(
        config_repository=MemoryConfigRepository(),
        account_manager=FakeAccountManager(),
        destinations_provider=destinations,
        test_sender=sender,
        event_log=events,
    )
    page.publish_checkbox.setChecked(True)
    page.account_combo.setCurrentIndex(page.account_combo.findData(7))
    page.destination_combo.setCurrentIndex(
        page.destination_combo.findData(-1001234567890)
    )

    assert page.test_send() is False
    assert dialogs
    assert expected_state in events.rows[-1]["message"]
    assert "telegram_account_id=7" in events.rows[-1]["message"]
    assert "telegram_channel_id=42" in events.rows[-1]["message"]
    assert "chat_id=-1001234567890" in events.rows[-1]["message"]
    assert page.test_button.isEnabled() is True
    page.close()


def test_async_test_send_success_uses_runner_logs_and_reenables(monkeypatch):
    app = QApplication.instance() or QApplication([])
    events = MemoryLogRepository()
    dialogs = []
    worker_thread = {}

    class Client:
        def __init__(self):
            self.messages = []

        def is_connected(self):
            return True

        async def send_message(self, chat_id, text):
            self.messages.append((chat_id, text))

    class Manager(FakeAccountManager):
        def __init__(self):
            super().__init__()
            self.client = Client()

        def peek_client(self, account_id):
            return self.client if account_id == 7 else None

    class Runner:
        def run(self, coroutine, timeout):
            import asyncio

            return asyncio.run(coroutine)

    manager = Manager()

    def show_information(*args):
        assert worker_thread["value"].isRunning() is False
        dialogs.append(args[-1])

    monkeypatch.setattr(
        QMessageBox,
        "information",
        show_information,
    )
    page = InternalSourceSettingsPage(
        config_repository=MemoryConfigRepository(),
        account_manager=manager,
        destinations_provider=destinations,
        async_runner=Runner(),
        event_log=events,
    )
    page.publish_checkbox.setChecked(True)
    page.account_combo.setCurrentIndex(page.account_combo.findData(7))
    page.destination_combo.setCurrentIndex(
        page.destination_combo.findData(-1001234567890)
    )

    assert page.test_send() is True
    worker_thread["value"] = page._workers[0]["thread"]
    deadline = time.time() + 2
    while page._workers and time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)

    assert manager.client.messages == [
        (
            -1001234567890,
            "Kraken: conexión de publicación verificada.",
        )
    ]
    assert dialogs
    assert "ÉXITO" in events.rows[-1]["message"]
    assert page.test_button.isEnabled() is True
    assert worker_thread["value"].isRunning() is False
    assert QApplication.activeModalWidget() is None
    page.close()


def test_async_future_exception_is_visible_logged_and_reenables(monkeypatch):
    app = QApplication.instance() or QApplication([])
    events = MemoryLogRepository()
    dialogs = []

    class Client:
        def is_connected(self):
            return True

        async def send_message(self, *_):
            return None

    class Manager(FakeAccountManager):
        def peek_client(self, account_id):
            return Client() if account_id == 7 else None

    class FailingRunner:
        def run(self, coroutine, timeout):
            coroutine.close()
            raise RuntimeError("Future completed with exception")

    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda *args: dialogs.append(args[-1]),
    )
    page = InternalSourceSettingsPage(
        config_repository=MemoryConfigRepository(),
        account_manager=Manager(),
        destinations_provider=destinations,
        async_runner=FailingRunner(),
        event_log=events,
    )
    page.publish_checkbox.setChecked(True)
    page.account_combo.setCurrentIndex(page.account_combo.findData(7))
    page.destination_combo.setCurrentIndex(
        page.destination_combo.findData(-1001234567890)
    )

    assert page.test_send() is True
    deadline = time.time() + 2
    while page._workers and time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)

    assert dialogs
    assert "Future completed with exception" in dialogs[-1]
    assert "ERROR" in events.rows[-1]["message"]
    assert page.test_button.isEnabled() is True
    page.close()


def test_refresh_destinations_preserves_valid_selection():
    app = QApplication.instance() or QApplication([])
    page = InternalSourceSettingsPage(
        config_repository=MemoryConfigRepository(),
        account_manager=FakeAccountManager(),
        destinations_provider=destinations,
        test_sender=lambda *_: None,
    )
    page.publish_checkbox.setChecked(True)
    page.account_combo.setCurrentIndex(page.account_combo.findData(7))
    page.destination_combo.setCurrentIndex(
        page.destination_combo.findData(-1001234567890)
    )
    assert page.refresh_destinations() == 1
    assert page.destination_combo.currentData() == -1001234567890
    assert page.destination_status_label.text() == "Válido"
    page.close()
