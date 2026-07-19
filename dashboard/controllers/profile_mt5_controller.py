from services.profile_mt5_service import profile_mt5_service


class ProfileMT5Controller:

    # ---------------------------------------------------------

    def get_accounts(self, profile_id):

        return profile_mt5_service.get_accounts(profile_id)

    # ---------------------------------------------------------

    def add_account(
        self,
        profile_id,
        account_id,
        priority=1,
    ):

        profile_mt5_service.add_account(
            profile_id=profile_id,
            account_id=account_id,
            priority=priority,
        )

    # ---------------------------------------------------------

    def remove_account(
        self,
        profile_id,
        account_id,
    ):

        profile_mt5_service.remove_account(
            profile_id=profile_id,
            account_id=account_id,
        )


profile_mt5_controller = ProfileMT5Controller()