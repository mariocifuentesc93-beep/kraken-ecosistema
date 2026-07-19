from repositories.profile_mt5_repository import profile_mt5_repository


class ProfileMT5Service:

    # ---------------------------------------------------------

    def get_accounts(self, profile_id):

        return profile_mt5_repository.get_accounts(profile_id)

    # ---------------------------------------------------------

    def add_account(
        self,
        profile_id,
        account_id,
        priority=1,
    ):

        profile_mt5_repository.add_account(
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

        profile_mt5_repository.remove_account(
            profile_id=profile_id,
            account_id=account_id,
        )


profile_mt5_service = ProfileMT5Service()