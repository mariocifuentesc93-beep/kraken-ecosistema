import os
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


def destinations(account_id):
    if account_id != 7:
        return []
    return [
        {
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


def test_test_send_validates_without_saving_configuration(monkeypatch):
    app = QApplication.instance() or QApplication([])
    repository = MemoryConfigRepository()
    manager = FakeAccountManager()
    sent = []
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)
    page = InternalSourceSettingsPage(
        config_repository=repository,
        account_manager=manager,
        destinations_provider=destinations,
        test_sender=lambda account, chat: sent.append((account, chat)),
    )
    page.publish_checkbox.setChecked(True)
    page.account_combo.setCurrentIndex(page.account_combo.findData(7))
    page.destination_combo.setCurrentIndex(
        page.destination_combo.findData(-1001234567890)
    )

    assert page.test_send() is True
    assert repository.config == InternalPublicationConfig()
    assert sent == [(7, -1001234567890)]
    page.close()


def test_disconnected_account_blocks_test_send(monkeypatch):
    app = QApplication.instance() or QApplication([])
    repository = MemoryConfigRepository()
    manager = FakeAccountManager(connected=False)
    errors = []
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
    )
    page.publish_checkbox.setChecked(True)
    page.account_combo.setCurrentIndex(page.account_combo.findData(7))
    page.destination_combo.setCurrentIndex(
        page.destination_combo.findData(-1001234567890)
    )

    assert page.test_button.isEnabled() is False
    assert page.test_send() is False
    assert "Cuenta desconectada" in errors[-1]
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
