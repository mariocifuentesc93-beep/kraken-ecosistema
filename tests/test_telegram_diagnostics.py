import asyncio
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from database.database_manager import database_manager
from models.profile import Profile
from models.telegram_account import TelegramAccount
from repositories.profile_repository import profile_repository
from repositories.profile_telegram_repository import profile_telegram_channel_repository
from repositories.telegram_account_repository import telegram_account_repository
from repositories.telegram_diagnostics_repository import telegram_diagnostics_repository
from services.telegram_diagnostics import TelegramDiagnostics
from telegram.async_runner import AsyncioThreadRunner


class PasswordRequiredError(Exception):
    pass


PasswordRequiredError.__name__ = "SessionPasswordNeededError"


class FakeClient:
    def __init__(self, authorized=False, fail_connect=False, password_required=False, inaccessible=False):
        self.connected = False
        self.authorized = authorized
        self.fail_connect = fail_connect
        self.password_required = password_required
        self.inaccessible = inaccessible
        self.code_sent = False

    def is_connected(self): return self.connected
    async def connect(self):
        if self.fail_connect: raise OSError("network unavailable")
        self.connected = True
    async def disconnect(self): self.connected = False
    async def is_user_authorized(self): return self.authorized
    async def send_code_request(self, phone): self.code_sent = True
    async def sign_in(self, *args, **kwargs):
        if self.password_required and "password" not in kwargs: raise PasswordRequiredError()
        self.authorized = True
    async def get_me(self): return SimpleNamespace(id=77, username="kraken_user", first_name="Kraken", last_name="Bot")
    async def get_entity(self, chat_id):
        if self.inaccessible: raise ValueError("access denied")
        return SimpleNamespace(title=f"Channel {chat_id}")


class LoopBoundFakeClient(FakeClient):
    def __init__(self):
        super().__init__()
        self.loop_ids = []

    def _record_loop(self):
        self.loop_ids.append(id(asyncio.get_running_loop()))

    async def connect(self):
        self._record_loop()
        await super().connect()

    async def send_code_request(self, phone):
        self._record_loop()
        await super().send_code_request(phone)

    async def sign_in(self, *args, **kwargs):
        self._record_loop()
        await super().sign_in(*args, **kwargs)

    async def is_user_authorized(self):
        self._record_loop()
        return await super().is_user_authorized()


class TelegramDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.original = database_manager.database; database_manager.close()
        self.directory = Path(tempfile.mkdtemp()); database_manager.database = self.directory / "telegram.db"
        database_manager.initialize()
        self.account = telegram_account_repository.create(TelegramAccount(
            name="Telegram", phone="+573001234567", api_id=1, api_hash="hash", session_name=str(self.directory / "session"),
        ))

    def tearDown(self):
        database_manager.close(); database_manager.database = self.original; shutil.rmtree(self.directory)

    def service(self, client, package=True):
        return TelegramDiagnostics(client_factory=lambda *args: client, package_available=package)

    def test_package_missing_missing_credentials_and_connection_failure(self):
        report = asyncio.run(self.service(FakeClient(), False).test_connection(self.account))
        self.assertEqual(report["status"], TelegramDiagnostics.NOT_CONFIGURED)
        missing = TelegramAccount(name="Missing")
        report = asyncio.run(self.service(FakeClient()).test_connection(missing))
        self.assertEqual(report["status"], TelegramDiagnostics.NOT_CONFIGURED)
        report = asyncio.run(self.service(FakeClient(fail_connect=True)).test_connection(self.account))
        self.assertEqual(report["status"], TelegramDiagnostics.ERROR)

    def test_unauthorized_code_and_password_required_states(self):
        client = FakeClient()
        service = self.service(client)
        report = asyncio.run(service.test_connection(self.account))
        self.assertEqual(report["status"], TelegramDiagnostics.CODE_REQUIRED)
        report = asyncio.run(service.start_authorization(self.account))
        self.assertEqual(report["status"], TelegramDiagnostics.CODE_REQUIRED)
        self.assertTrue(client.code_sent)
        password_client = FakeClient(password_required=True)
        report = asyncio.run(self.service(password_client).verify_code(self.account, "12345"))
        self.assertEqual(report["status"], TelegramDiagnostics.PASSWORD_REQUIRED)

    def test_successful_authorization_persistence_and_exports(self):
        report = asyncio.run(self.service(FakeClient(authorized=True)).test_connection(self.account))
        self.assertEqual(report["status"], TelegramDiagnostics.AUTHORIZED)
        self.assertEqual(report["username"], "kraken_user")
        self.assertEqual(telegram_account_repository.get_by_id(self.account.id).user_id, 77)
        self.assertIsNotNone(telegram_diagnostics_repository.latest(self.account.id))
        service = self.service(FakeClient(authorized=True))
        service.export_json(report, self.directory / "diagnostic.json")
        service.export_text(report, self.directory / "diagnostic.txt")
        self.assertTrue((self.directory / "diagnostic.json").exists())

    def test_inaccessible_and_valid_configured_channels(self):
        profile = profile_repository.create(Profile(name="Telegram profile"))
        profile_telegram_channel_repository.create_channel(100, "Configured", profile.id, self.account.id)
        inaccessible = asyncio.run(self.service(FakeClient(authorized=True, inaccessible=True)).test_connection(self.account))
        self.assertEqual(len(inaccessible["channels"]), 1)
        self.assertFalse(inaccessible["channels"][0]["accessible"])
        valid = asyncio.run(self.service(FakeClient(authorized=True)).test_connection(self.account))
        self.assertTrue(valid["channels"][0]["accessible"])
        self.assertTrue(valid["channels"][0]["enabled"])

    def test_safe_disconnect_and_session_deletion(self):
        session = Path(self.account.session_name + ".session"); session.write_text("local")
        client = FakeClient(authorized=True); service = self.service(client)
        asyncio.run(service.test_connection(self.account))
        report = asyncio.run(service.disconnect(self.account))
        self.assertEqual(report["status"], TelegramDiagnostics.DISCONNECTED)
        asyncio.run(service.delete_local_session(self.account))
        self.assertFalse(session.exists())

    def test_authorization_reuses_one_persistent_event_loop(self):
        client = LoopBoundFakeClient()
        service = self.service(client)
        runner = AsyncioThreadRunner("TelegramAuthorizationTest")
        try:
            sent = runner.run(service.start_authorization(self.account))
            self.assertEqual(sent["status"], TelegramDiagnostics.CODE_REQUIRED)
            authorized = runner.run(
                service.verify_code(self.account, "12345")
            )
            self.assertEqual(
                authorized["status"],
                TelegramDiagnostics.AUTHORIZED,
            )
            self.assertGreaterEqual(len(client.loop_ids), 4)
            self.assertEqual(len(set(client.loop_ids)), 1)
            runner.run(service.disconnect_all())
        finally:
            runner.shutdown()


if __name__ == "__main__":
    unittest.main()
