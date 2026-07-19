from telethon import TelegramClient
import asyncio

from repositories.telegram_account_repository import telegram_account_repository


class TelegramAccountManager:

    def __init__(self):

        self.clients = {}

        self.accounts = []

        self.active_account = None

        self.reload()

    # ==========================================================
    # CARGA
    # ==========================================================

    def reload(self):

        self.accounts = telegram_account_repository.get_enabled()

        self.active_account = None

        if self.accounts:

            for account in self.accounts:

                if getattr(account, "auto_connect", False):

                    self.active_account = account

                    break

            if self.active_account is None:

                self.active_account = self.accounts[0]

        return True

    # ==========================================================
    # CUENTAS
    # ==========================================================

    def get_accounts(self):

        return self.accounts

    def get_account(self, account_id):

        for account in self.accounts:

            if account.id == account_id:

                return account

        return None

    def get_active_account(self):

        return self.active_account

    def set_active_account(self, account_id):

        account = self.get_account(account_id)

        if account:

            self.active_account = account

        return self.active_account

    # ==========================================================
    # CLIENTES
    # ==========================================================

    def create_client(self, account_id=None):

        account = (
            self.get_active_account()
            if account_id is None
            else self.get_account(account_id)
        )

        if account is None:

            return None

        return TelegramClient(
            account.session_name,
            int(account.api_id),
            account.api_hash,
        )

    def get_client(self, account_id=None):

        account = (
            self.get_active_account()
            if account_id is None
            else self.get_account(account_id)
        )

        if account is None:

            return None

        if account.id not in self.clients:

            self.clients[account.id] = self.create_client(account.id)

        return self.clients[account.id]

    def get_clients(self):

        return self.clients

    # ==========================================================
    # ESTADO
    # ==========================================================

    def is_connected(self, account_id=None):

        client = self.get_client(account_id)

        if client is None:

            return False

        return client.is_connected()

    def is_authorized(self, account_id=None):

        client = self.get_client(account_id)

        if client is None:

            return False

        try:

            return client.is_user_authorized()

        except Exception:

            return False

    # ==========================================================
    # CICLO DE VIDA
    # ==========================================================

    async def connect(self, account_id=None):

        client = self.get_client(account_id)

        if client is None:

            return None

        if not client.is_connected():

            await client.connect()

        return client

    async def disconnect(self, account_id=None):

        client = self.get_client(account_id)

        if client is None:

            return

        if client.is_connected():

            await client.disconnect()

    async def disconnect_all(self):
        for client in list(self.clients.values()):
            try:
                if client.is_connected():
                    await client.disconnect()
            except Exception:
                # A previously closed Telethon loop does not prevent the rest
                # of the application shutdown sequence from completing.
                pass
        self.clients.clear()

    def shutdown(self):
        """Disconnect clients before the Qt event loop and Python exit."""
        if not self.clients:
            return
        try:
            asyncio.run(self.disconnect_all())
        except RuntimeError:
            # Qt invokes shutdown on its main thread, where no asyncio loop is
            # normally running. Leave ownership with an active external loop.
            pass


telegram_account_manager = TelegramAccountManager()
