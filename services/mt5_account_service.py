from models.mt5_account import MT5Account
from repositories.mt5_account_repository import mt5_account_repository


class MT5AccountService:

    # ---------------------------------------------------------

    def get_all(self):

        return mt5_account_repository.get_all()

    # ---------------------------------------------------------

    def get(self, account_id):

        return mt5_account_repository.get_by_id(account_id)

    # ---------------------------------------------------------

    def create(
        self,
        name,
        login,
        password,
        server,
        terminal_path,
        magic_number=10001,
        active=True,
        auto_connect=True,
        reconnect=True,
        description="",
    ):

        account = MT5Account(

            name=name,

            login=login,

            password=password,

            server=server,

            terminal_path=terminal_path,

            magic_number=magic_number,

            active=active,

            auto_connect=auto_connect,

            reconnect=reconnect,

            description=description,

        )

        return mt5_account_repository.create(account)

    # ---------------------------------------------------------

    def update(self, account):

        return mt5_account_repository.update(account)

    # ---------------------------------------------------------

    def delete(self, account_id):

        mt5_account_repository.delete(account_id)


mt5_account_service = MT5AccountService()