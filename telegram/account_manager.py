from telethon import TelegramClient
import asyncio

from repositories.telegram_account_repository import telegram_account_repository


class TelegramAccountManager:

    def __init__(self):

        self.clients = {}

        self.accounts = []

        self.active_account = None
        self._connection_states = {}
        self._last_errors = {}

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

    def register_client(self, account_id, client):
        """Share a client created by diagnostics with the runtime registry."""
        if account_id is not None and client is not None:
            self.clients[account_id] = client
        return client

    def peek_client(self, account_id=None):
        """Return an existing client without creating a Telethon session."""
        account = (
            self.get_active_account()
            if account_id is None
            else self.get_account(account_id)
        )
        return self.clients.get(account.id) if account is not None else None

    def connection_state(self, account_id=None):
        """Return real state without creating or connecting a client."""
        account = (
            self.get_active_account()
            if account_id is None
            else self.get_account(account_id)
        )
        if account is None:
            return "DISCONNECTED"
        state = self._connection_states.get(account.id)
        if state == "CONNECTING":
            return state
        client = self.peek_client(account.id)
        try:
            if client is not None and client.is_connected():
                return "CONNECTED"
        except Exception as error:
            self._last_errors[account.id] = str(error)
            return "ERROR"
        if self._last_errors.get(account.id) or getattr(
            account,
            "last_error",
            "",
        ):
            return "ERROR"
        return "DISCONNECTED"

    def last_error(self, account_id=None):
        account = (
            self.get_active_account()
            if account_id is None
            else self.get_account(account_id)
        )
        if account is None:
            return ""
        return self._last_errors.get(
            account.id,
            str(getattr(account, "last_error", "") or ""),
        )

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

    async def connect(self, account_id=None, timeout=10, retries=2):

        client = self.get_client(account_id)

        if client is None:

            raise ValueError("No existe una cuenta Telegram habilitada.")

        account = (
            self.get_active_account()
            if account_id is None
            else self.get_account(account_id)
        )
        self._connection_states[account.id] = "CONNECTING"
        self._last_errors[account.id] = ""
        for attempt in range(retries + 1):
            try:
                if not client.is_connected():
                    await asyncio.wait_for(client.connect(), timeout=timeout)
                self._connection_states[account.id] = "CONNECTED"
                return client
            except (asyncio.TimeoutError, OSError) as error:
                if attempt == retries:
                    self._connection_states[account.id] = "ERROR"
                    self._last_errors[account.id] = str(error)
                    raise ConnectionError(f"Telegram no respondió: {error}") from error
                await asyncio.sleep(0.25 * (attempt + 1))
            except Exception as error:
                self._connection_states[account.id] = "ERROR"
                self._last_errors[account.id] = str(error)
                raise

    async def test_connection(self, account_id=None, timeout=10, retries=2):
        account = self.get_account(account_id)
        if account is None or not account.api_id or not account.api_hash or not account.phone:
            return False, False, "Faltan API ID, API hash o teléfono de Telegram."
        try:
            client = await self.connect(account_id, timeout, retries)
            authorized = await asyncio.wait_for(
                client.is_user_authorized(), timeout=timeout
            )
            return True, bool(authorized), (
                "Cuenta Telegram autorizada."
                if authorized else "La cuenta no está autorizada; complete la autorización de Telethon."
            )
        except (ConnectionError, asyncio.TimeoutError, OSError) as error:
            return False, False, str(error)

    async def disconnect(self, account_id=None, timeout=10):

        client = self.get_client(account_id)

        if client is None:

            return

        if client.is_connected():

            await asyncio.wait_for(client.disconnect(), timeout=timeout)
        account = (
            self.get_active_account()
            if account_id is None
            else self.get_account(account_id)
        )
        if account is not None:
            self._connection_states[account.id] = "DISCONNECTED"
            self._last_errors[account.id] = ""
            account.last_error = ""

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
        self._connection_states.clear()

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
