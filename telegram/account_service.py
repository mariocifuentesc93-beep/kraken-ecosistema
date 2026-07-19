from telegram.account_manager import telegram_account_manager


class TelegramAccountService:

    # ==========================================================
    # CUENTAS
    # ==========================================================

    def get_active_account(self):

        return telegram_account_manager.get_active_account()

    def set_active_account(self, account_id):

        return telegram_account_manager.set_active_account(account_id)

    def get_account(self, account_id):

        return telegram_account_manager.get_account(account_id)

    def get_accounts(self):

        return telegram_account_manager.get_accounts()

    # ==========================================================
    # CLIENTES
    # ==========================================================

    def get_client(self, account_id=None):

        return telegram_account_manager.get_client(account_id)

    def get_clients(self):

        return telegram_account_manager.get_clients()

    def create_client(self, account_id=None):

        return telegram_account_manager.create_client(account_id)

    # ==========================================================
    # INFORMACIÓN
    # ==========================================================

    def get_phone(self):

        account = self.get_active_account()

        return account.phone if account else ""

    def get_session(self):

        account = self.get_active_account()

        return account.session_name if account else ""

    def get_username(self):

        account = self.get_active_account()

        return account.username if account else ""

    def get_name(self):

        account = self.get_active_account()

        if account is None:
            return ""

        first = account.first_name or ""
        last = account.last_name or ""

        return f"{first} {last}".strip()

    # ==========================================================
    # ESTADO
    # ==========================================================

    def is_connected(self, account_id=None):

        return telegram_account_manager.is_connected(account_id)

    def is_authorized(self, account_id=None):

        return telegram_account_manager.is_authorized(account_id)

    # ==========================================================
    # CICLO DE VIDA
    # ==========================================================

    def connect(self, account_id=None):

        return telegram_account_manager.connect(account_id)

    def disconnect(self, account_id=None):

        return telegram_account_manager.disconnect(account_id)

    def reconnect(self, account_id=None):

        self.disconnect(account_id)

        return self.connect(account_id)

    # ==========================================================
    # RECARGA
    # ==========================================================

    def reload(self):

        return telegram_account_manager.reload()


telegram_account_service = TelegramAccountService()