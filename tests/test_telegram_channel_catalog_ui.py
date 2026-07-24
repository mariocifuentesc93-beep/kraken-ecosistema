import os
import sqlite3

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from dashboard.pages.channels_page import ChannelsPage
from database.schema import create_tables
from models.internal_publication_config import InternalPublicationConfig
from models.telegram_account import TelegramAccount


class Accounts:
    def get_all(self):
        return []

    def get_by_id(self, _account_id):
        return None


class Channels:
    def list_by_account(self, _account_id):
        return []

    def get_by_id(self, _channel_id):
        return None


def test_channels_page_is_global_catalog_without_profile_selector():
    app = QApplication.instance() or QApplication([])
    page = ChannelsPage(
        account_repository=Accounts(),
        channel_repository=Channels(),
        sync_service=object(),
    )

    assert hasattr(page, "account_combo")
    assert not hasattr(page, "profile_combo")
    assert page.table.columnCount() == 8
    assert "Perfil" not in [
        page.table.horizontalHeaderItem(index).text()
        for index in range(page.table.columnCount())
    ]
    assert "No hay ninguna cuenta" in page.status_label.text()
    page.deleteLater()


class SqliteAccounts:
    def __init__(self, connection):
        self.connection = connection

    def _select(self, where="", parameters=()):
        rows = self.connection.execute(
            f"SELECT * FROM telegram_accounts {where} ORDER BY name",
            parameters,
        ).fetchall()
        return [TelegramAccount(**dict(row)) for row in rows]

    def get_all(self):
        return self._select()

    def get_enabled(self):
        return self._select("WHERE enabled=1")

    def get_by_id(self, account_id):
        accounts = self._select("WHERE id=?", (account_id,))
        return accounts[0] if accounts else None


class AccountManager:
    def __init__(self, repository):
        self.repository = repository
        self.accounts = []

    def reload(self):
        self.accounts = self.repository.get_enabled()
        return True

    def get_accounts(self):
        return self.accounts

    def get_account(self, account_id):
        return self.repository.get_by_id(account_id)

    def connection_state(self, account_id):
        account = self.get_account(account_id)
        return (
            "CONNECTED"
            if account and account.connected and account.authorized
            else "DISCONNECTED"
        )


class InternalConfig:
    def get(self):
        return InternalPublicationConfig()

    def save(self, config):
        return config


def test_authorized_global_account_is_visible_across_telegram_pages(
    tmp_path,
    monkeypatch,
):
    from dashboard.pages import telegram_accounts_page as telegram_page_module
    from dashboard.pages.internal_source_settings_page import (
        InternalSourceSettingsPage,
    )

    app = QApplication.instance() or QApplication([])
    connection = sqlite3.connect(tmp_path / "telegram-catalog-ui.db")
    connection.row_factory = sqlite3.Row
    create_tables(connection)
    accounts = SqliteAccounts(connection)
    channels = Channels()

    channels_page = ChannelsPage(
        account_repository=accounts,
        channel_repository=channels,
        sync_service=object(),
    )
    assert "No hay ninguna cuenta" in channels_page.status_label.text()

    connection.execute(
        """
        INSERT INTO telegram_accounts (
            id, name, phone, api_id, api_hash, session_name,
            enabled, auto_connect, connected, authorized
        )
        VALUES (7, 'Cuenta operativa', '+570000000000', 12345, 'hash',
                'test-session', 1, 1, 1, 1)
        """
    )
    connection.commit()
    manager = AccountManager(accounts)
    manager.reload()
    monkeypatch.setattr(
        telegram_page_module,
        "telegram_account_repository",
        accounts,
    )
    monkeypatch.setattr(
        telegram_page_module,
        "telegram_account_manager",
        manager,
    )

    telegram_page = telegram_page_module.TelegramAccountsPage()
    internal_page = InternalSourceSettingsPage(
        config_repository=InternalConfig(),
        account_manager=manager,
        destinations_provider=lambda _account_id: [],
        test_sender=lambda _account_id, _chat_id: None,
    )

    channels_page.refresh()

    assert telegram_page.table.rowCount() == 1
    assert telegram_page.table.item(0, 0).text() == "7"
    assert channels_page.account_combo.findData(7) >= 0
    assert channels_page.account_combo.currentData() == 7
    assert "No hay ninguna cuenta" not in channels_page.status_label.text()
    assert internal_page.account_combo.findData(7) >= 0

    channels_page.refresh()
    assert channels_page.account_combo.currentData() == 7

    internal_page.deleteLater()
    telegram_page.deleteLater()
    channels_page.deleteLater()
    connection.close()
