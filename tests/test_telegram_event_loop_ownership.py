import asyncio
import time
from types import SimpleNamespace

from services.runtime_coordinator import TelegramListenerRuntime
from services.telegram_channel_sync_service import TelegramChannelSyncService
from services.telegram_diagnostics import TelegramDiagnostics
from telegram.async_runner import AsyncioThreadRunner


class LoopBoundClient:
    def __init__(self):
        self.connected = False
        self.loop_ids = []
        self.dialogs_requested = 0

    def _record_loop(self):
        self.loop_ids.append(id(asyncio.get_running_loop()))

    def is_connected(self):
        return self.connected

    async def connect(self):
        self._record_loop()
        self.connected = True

    async def disconnect(self):
        self._record_loop()
        self.connected = False

    async def is_user_authorized(self):
        self._record_loop()
        return True

    def iter_dialogs(self):
        async def generate():
            self._record_loop()
            self.dialogs_requested += 1
            entity = SimpleNamespace(
                left=False,
                broadcast=True,
                creator=True,
                admin_rights=None,
                username="kraken",
            )
            yield SimpleNamespace(
                id=-100123,
                name="Señales Kraken",
                entity=entity,
            )

        return generate()


class SharedManager:
    def __init__(self, account, client):
        self.account = account
        self.clients = {}
        self.client = client

    def reload(self):
        return True

    def get_account(self, account_id):
        return self.account if account_id == self.account.id else None

    def get_active_account(self):
        return self.account

    def peek_client(self, account_id):
        return self.clients.get(account_id)

    def register_client(self, account_id, client):
        self.clients[account_id] = client
        return client

    def unregister_client(self, account_id):
        return self.clients.pop(account_id, None)

    async def connect(self, account_id):
        client = self.clients.get(account_id)
        assert client is self.client
        if not client.is_connected():
            await client.connect()
        return client

    async def disconnect(self, account_id):
        client = self.clients.get(account_id)
        if client and client.is_connected():
            await client.disconnect()

    async def list_dialog_catalog(self, account_id):
        client = self.clients.get(account_id)
        assert client is self.client
        result = []
        async for dialog in client.iter_dialogs():
            result.append(
                {
                    "chat_id": dialog.id,
                    "name": dialog.name,
                    "username": dialog.entity.username,
                    "chat_type": "CANAL",
                    "can_read": True,
                    "can_send": True,
                }
            )
        return result


class Accounts:
    def __init__(self, account):
        self.account = account

    def get_by_id(self, account_id):
        return self.account if account_id == self.account.id else None


class Channels:
    def __init__(self):
        self.saved = []

    def synchronize(self, account_id, dialogs):
        self.saved = list(dialogs)
        return self.saved


def test_authorization_runtime_and_channel_sync_share_client_and_loop():
    account = SimpleNamespace(
        id=7,
        authorized=True,
        session_name="unused-test-session",
        api_id=1,
        api_hash="hash",
    )
    client = LoopBoundClient()
    manager = SharedManager(account, client)
    client_factory_calls = []

    def client_factory(*_args):
        client_factory_calls.append(True)
        return client

    diagnostics = TelegramDiagnostics(
        client_factory=client_factory,
        package_available=True,
        account_manager=manager,
    )
    runner = AsyncioThreadRunner("TelegramSharedLoopRegression")
    runtime = TelegramListenerRuntime(
        account_manager=manager,
        listener_factory=lambda *_args, **_kwargs: None,
        async_runner=runner,
    )
    channels = Channels()
    sync = TelegramChannelSyncService(
        account_repository=Accounts(account),
        channel_repository=channels,
        account_manager=manager,
    )

    try:
        authorized_client = diagnostics._client(account)
        runner.run(authorized_client.connect())
        runtime.start()
        deadline = time.time() + 2
        while len(client.loop_ids) < 3 and time.time() < deadline:
            time.sleep(0.01)

        result = runner.run(sync.synchronize(account.id))

        assert manager.peek_client(account.id) is authorized_client
        assert len(client_factory_calls) == 1
        assert result[0]["chat_id"] == -100123
        assert client.dialogs_requested == 1
        assert len(set(client.loop_ids)) == 1
    finally:
        runtime.stop()
        runner.shutdown()
