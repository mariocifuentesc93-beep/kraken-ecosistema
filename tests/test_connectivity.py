import asyncio
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from database.database_manager import database_manager
from models.mt5_account import MT5Account
from models.profile import Profile
from models.telegram_account import TelegramAccount
from mt5.connector import MT5Connector
from repositories.mt5_account_repository import mt5_account_repository
from repositories.profile_repository import profile_repository
from repositories.telegram_account_repository import telegram_account_repository
from telegram.account_manager import telegram_account_manager
from utils.live_readiness import live_mode_issues


class ConnectivityTests(unittest.TestCase):
    def setUp(self):
        self.original_database = database_manager.database
        database_manager.close()
        self.temporary_directory = Path(tempfile.mkdtemp())
        database_manager.database = self.temporary_directory / "connectivity.db"
        database_manager.initialize()
        telegram_account_manager.clients.clear()
        telegram_account_manager.reload()

    def tearDown(self):
        database_manager.close()
        database_manager.database = self.original_database
        shutil.rmtree(self.temporary_directory)

    def test_missing_and_invalid_mt5_credentials(self):
        connector = MT5Connector()
        self.assertFalse(connector.login(MT5Account(), retries=0))
        self.assertIn("Faltan", connector.last_error)

        account = MT5Account(name="Invalid", login=1, password="bad", server="broker")
        with patch("mt5.connector.mt5") as mt5:
            mt5.initialize.return_value = True
            mt5.login.return_value = False
            mt5.last_error.return_value = "invalid credentials"
            self.assertFalse(connector.login(account, timeout_ms=1, retries=0))
        self.assertIn("rechazadas", connector.last_error)

    def test_mt5_and_telegram_account_crud_persistence(self):
        mt5_account = mt5_account_repository.create(
            MT5Account(name="CRUD MT5", login=100, password="pw", server="broker")
        )
        telegram_account = telegram_account_repository.create(
            TelegramAccount(
                name="CRUD Telegram", phone="+10000000002", api_id=3,
                api_hash="hash", session_name="crud-session",
            )
        )
        mt5_account.name = "Updated MT5"
        telegram_account.name = "Updated Telegram"
        self.assertTrue(mt5_account_repository.update(mt5_account))
        self.assertTrue(telegram_account_repository.update(telegram_account))
        database_manager.close()
        database_manager.initialize()
        self.assertEqual(mt5_account_repository.get_by_id(mt5_account.id).name, "Updated MT5")
        self.assertEqual(
            telegram_account_repository.get_by_id(telegram_account.id).name,
            "Updated Telegram",
        )
        self.assertTrue(mt5_account_repository.delete(mt5_account.id))
        self.assertTrue(telegram_account_repository.delete(telegram_account.id))

    def test_valid_simulated_mt5_connection(self):
        connector = MT5Connector()
        account = MT5Account(name="Simulated", login=1, password="ok", server="broker")
        with patch("mt5.connector.mt5") as mt5:
            mt5.initialize.return_value = True
            mt5.login.return_value = True
            mt5.account_info.return_value = Mock(
                balance=1000.0, equity=1000.0, margin_free=900.0
            )
            self.assertTrue(connector.login(account, timeout_ms=1, retries=0))
        self.assertTrue(connector.connected)
        self.assertEqual(account.balance, 1000.0)

    def test_mt5_connection_state_requires_selected_account_login_match(self):
        connector = MT5Connector()
        connector.account = MT5Account(
            name="DEMO",
            login=243274,
            password="ok",
            server="BridgeMarkets-MT5",
        )
        with patch("mt5.connector.mt5") as mt5:
            mt5.terminal_info.return_value = Mock()
            mt5.account_info.return_value = Mock(login=243274)

            self.assertTrue(connector.is_connected())
            self.assertEqual(connector.current_account, 243274)

            mt5.account_info.return_value = Mock(login=7911007)
            self.assertFalse(connector.is_connected())

    def test_mt5_connection_state_rejects_unselected_scanner_terminal(self):
        connector = MT5Connector()
        with patch("mt5.connector.mt5") as mt5:
            mt5.terminal_info.return_value = Mock()
            mt5.account_info.return_value = Mock(login=7911007)

            self.assertFalse(connector.is_connected())

    def test_missing_and_unauthorized_telegram_account(self):
        missing = telegram_account_repository.create(TelegramAccount(name="Missing"))
        telegram_account_manager.reload()
        connected, authorized, _ = asyncio.run(
            telegram_account_manager.test_connection(missing.id, retries=0)
        )
        self.assertFalse(connected)
        self.assertFalse(authorized)

        account = telegram_account_repository.create(
            TelegramAccount(
                name="Unauthorized", phone="+10000000000", api_id=1,
                api_hash="hash", session_name="test-session",
            )
        )
        telegram_account_manager.reload()
        client = Mock()
        client.is_connected.return_value = True

        async def unauthorized():
            return False

        client.is_user_authorized = unauthorized
        telegram_account_manager.clients[account.id] = client
        connected, authorized, message = asyncio.run(
            telegram_account_manager.test_connection(account.id, retries=0)
        )
        self.assertTrue(connected)
        self.assertFalse(authorized)
        self.assertIn("no está autorizada", message)

    def test_valid_simulated_telegram_and_live_blocker(self):
        account = telegram_account_repository.create(
            TelegramAccount(
                name="Authorized", phone="+10000000001", api_id=2,
                api_hash="hash", session_name="valid-session",
            )
        )
        telegram_account_manager.reload()
        client = Mock()
        client.is_connected.return_value = True

        async def authorized():
            return True

        client.is_user_authorized = authorized
        telegram_account_manager.clients[account.id] = client
        connected, authorized_status, _ = asyncio.run(
            telegram_account_manager.test_connection(account.id, retries=0)
        )
        self.assertTrue(connected)
        self.assertTrue(authorized_status)

        profile = profile_repository.create(Profile(name="Live blocked", execution_mode="LIVE"))
        issues = live_mode_issues(profile)
        self.assertIn("El perfil no tiene una cuenta MT5 predeterminada.", issues)


if __name__ == "__main__":
    unittest.main()
