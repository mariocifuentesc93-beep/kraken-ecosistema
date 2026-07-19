from models.mt5_account import MT5Account
from repositories.mt5_account_repository import mt5_account_repository


class MT5AccountManager:

    def create_account(
        self,
        name,
        login,
        password,
        server,
    ):

        return mt5_account_repository.create(
            MT5Account(
                name=name,
                login=login,
                password=password,
                server=server,
            )
        )

    def get_accounts(self):

        return mt5_account_repository.get_all()

    def get_active_account(self):

        return next(
            (account for account in self.get_accounts() if account.active),
            None,
        )

    def activate_account(self, account_id):

        account = mt5_account_repository.get_by_id(account_id)
        if account is None:
            return False
        account.active = True
        return bool(mt5_account_repository.update(account))


mt5_account_manager = MT5AccountManager()
