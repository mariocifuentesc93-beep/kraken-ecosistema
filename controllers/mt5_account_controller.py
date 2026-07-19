from services.mt5_account_service import mt5_account_service


class MT5AccountController:

    # ---------------------------------------------------------

    def get_all(self):

        return mt5_account_service.get_all()

    # ---------------------------------------------------------

    def get(self, account_id):

        return mt5_account_service.get(account_id)

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

        return mt5_account_service.create(
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

    # ---------------------------------------------------------

    def update(self, account):

        return mt5_account_service.update(account)

    # ---------------------------------------------------------

    def delete(self, account_id):

        mt5_account_service.delete(account_id)


mt5_account_controller = MT5AccountController()