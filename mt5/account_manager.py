from database.mt5_repository import (
    add_account,
    get_accounts,
    get_active_account,
    activate_account,
)


class MT5AccountManager:

    def create_account(
        self,
        name,
        login,
        password,
        server,
    ):

        add_account(
            name,
            login,
            password,
            server,
        )

    def get_accounts(self):

        return get_accounts()

    def get_active_account(self):

        return get_active_account()

    def activate_account(self, account_id):

        return activate_account(account_id)


mt5_account_manager = MT5AccountManager()