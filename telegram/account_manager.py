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
        self._loaded = False

    # ==========================================================
    # CARGA
    # ==========================================================

    def reload(self):

        self.accounts = telegram_account_repository.get_enabled()
        self._loaded = True

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
        if not self._loaded:
            self.reload()
        return self.accounts

    def get_account(self, account_id):
        if not self._loaded:
            self.reload()
        for account in self.accounts:

            if account.id == account_id:

                return account

        return None

    def get_active_account(self):
        if not self._loaded:
            self.reload()
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

    def unregister_client(self, account_id):
        """Forget a shared client without creating or reconnecting another."""
        return self.clients.pop(account_id, None)

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

    async def list_sendable_destinations(self, account_id):
        """Return dialogs where the already-connected account may send."""
        client = self.peek_client(account_id)
        if client is None or not client.is_connected():
            raise RuntimeError("La cuenta Telegram no está conectada.")
        destinations = []
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            if getattr(entity, "left", False):
                continue
            if getattr(entity, "broadcast", False):
                rights = getattr(entity, "admin_rights", None)
                if not (
                    getattr(entity, "creator", False)
                    or getattr(rights, "post_messages", False)
                ):
                    continue
                destination_type = "Canal"
            elif getattr(entity, "megagroup", False):
                destination_type = "Supergrupo"
            elif getattr(entity, "bot", False) or getattr(
                entity, "first_name", None
            ):
                destination_type = "Privado"
            else:
                destination_type = "Grupo"
            destinations.append(
                {
                    "title": dialog.name or str(dialog.id),
                    "type": destination_type,
                    "chat_id": int(dialog.id),
                }
            )
        return destinations

    async def list_dialog_catalog(self, account_id):
        """Return every readable dialog with account-scoped metadata."""
        client = self.peek_client(account_id)
        if client is None or not client.is_connected():
            raise RuntimeError("La cuenta Telegram no está conectada.")

        dialogs = []
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            if getattr(entity, "left", False):
                continue

            can_send = True
            if getattr(entity, "broadcast", False):
                rights = getattr(entity, "admin_rights", None)
                can_send = bool(
                    getattr(entity, "creator", False)
                    or getattr(rights, "post_messages", False)
                )
                chat_type = "CANAL"
            elif getattr(entity, "megagroup", False):
                rights = getattr(entity, "banned_rights", None)
                can_send = not bool(getattr(rights, "send_messages", False))
                chat_type = "SUPERGRUPO"
            elif getattr(entity, "bot", False) or getattr(
                entity, "first_name", None
            ):
                chat_type = "PRIVADO"
            else:
                rights = getattr(entity, "banned_rights", None)
                can_send = not bool(getattr(rights, "send_messages", False))
                chat_type = "GRUPO"

            dialogs.append(
                {
                    "chat_id": int(dialog.id),
                    "name": dialog.name or str(dialog.id),
                    "username": getattr(entity, "username", None),
                    "chat_type": chat_type,
                    "can_read": True,
                    "can_send": can_send,
                }
            )
        return dialogs

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
        from telegram.async_runner import telegram_async_runner

        if telegram_async_runner.running:
            telegram_async_runner.run(self.disconnect_all(), timeout=5)
        else:
            # A Telethon client must never be moved to a temporary event loop.
            # Normal application shutdown disconnects it before stopping the
            # persistent runner; this branch only forgets stale references.
            self.clients.clear()
            self._connection_states.clear()


telegram_account_manager = TelegramAccountManager()
