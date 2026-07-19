from mt5.account_manager import (
    mt5_account_manager,
)


class MT5AccountService:

    def get_active_account(self):

        return mt5_account_manager.get_active_account()

    def get_accounts(self):

        return mt5_account_manager.get_accounts()

    def activate_account(self, account_id):

        return mt5_account_manager.activate_account(account_id)


mt5_account_service = MT5AccountService()