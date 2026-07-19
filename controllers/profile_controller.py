from services.profile_service import profile_service


class ProfileController:

    # ---------------------------------------------------------

    def get_profiles(self):

        return profile_service.get_profiles()

    # ---------------------------------------------------------

    def get_all(self):

        return profile_service.get_all()

    # ---------------------------------------------------------

    def get(self, profile_id):

        return profile_service.get(profile_id)

    # ---------------------------------------------------------

    def create(
        self,
        name,
        description="",
        color="#00C853",
        icon="📈",
        active=True,
        enabled=True,
        operation_mode="telegram",
        telegram_account_id=None,
        default_mt5_account=None,
        risk_mode="PERCENT",
        risk_percent=2.0,
        risk_amount=0.0,
        fixed_lot=0.10,
    ):

        return profile_service.create(
            name=name,
            description=description,
            color=color,
            icon=icon,
            active=active,
            enabled=enabled,
            operation_mode=operation_mode,
            telegram_account_id=telegram_account_id,
            default_mt5_account=default_mt5_account,
            risk_mode=risk_mode,
            risk_percent=risk_percent,
            risk_amount=risk_amount,
            fixed_lot=fixed_lot,
        )

    # ---------------------------------------------------------

    def update(self, profile):

        return profile_service.update(profile)

    # ---------------------------------------------------------

    def delete(self, profile_id):

        profile_service.delete(profile_id)

    # ---------------------------------------------------------

    def duplicate(self, profile_id):

        return profile_service.duplicate(profile_id)
        # ---------------------------------------------------------

    def activate(self, profile_id):

        return profile_service.activate(profile_id)

    # ---------------------------------------------------------

    def deactivate(self, profile_id):

        return profile_service.deactivate(profile_id)


profile_controller = ProfileController()