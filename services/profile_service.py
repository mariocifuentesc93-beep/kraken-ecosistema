from models.profile import Profile
from repositories.profile_repository import profile_repository


class ProfileService:

    # ---------------------------------------------------------

    def get_profiles(self):

        return profile_repository.get_all()

    # ---------------------------------------------------------

    def get_all(self):

        return profile_repository.get_all()

    # ---------------------------------------------------------

    def get(self, profile_id):

        return profile_repository.get_by_id(profile_id)

    # ---------------------------------------------------------

    def exists(self, profile_id):

        return self.get(profile_id) is not None

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

        profile = Profile(

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

        return profile_repository.create(profile)

    # ---------------------------------------------------------

    def update(self, profile):

        return profile_repository.update(profile)

    # ---------------------------------------------------------

    def save(self, profile):

        if getattr(profile, "id", None):

            return self.update(profile)

        return self.create(

            name=profile.name,

            description=profile.description,

            color=profile.color,

            icon=profile.icon,

            active=profile.active,

            enabled=getattr(profile, "enabled", True),

            operation_mode=profile.operation_mode,

            telegram_account_id=getattr(profile, "telegram_account_id", None),

            default_mt5_account=getattr(profile, "default_mt5_account", None),

            risk_mode=getattr(profile, "risk_mode", "PERCENT"),

            risk_percent=getattr(profile, "risk_percent", 2.0),

            risk_amount=getattr(profile, "risk_amount", 0.0),

            fixed_lot=getattr(profile, "fixed_lot", 0.10),

        )

    # ---------------------------------------------------------

    def delete(self, profile_id):

        return profile_repository.delete(profile_id)

    # ---------------------------------------------------------

    def duplicate(self, profile_id):

        return profile_repository.duplicate(profile_id)

    # ---------------------------------------------------------

    def activate(self, profile_id):

        profile = self.get(profile_id)

        if profile is None:

            return False

        profile.active = True

        profile.enabled = True

        profile_repository.update(profile)

        return True

    # ---------------------------------------------------------

    def deactivate(self, profile_id):

        profile = self.get(profile_id)

        if profile is None:

            return False

        profile.active = False

        profile.enabled = False

        profile_repository.update(profile)

        return True

    # ---------------------------------------------------------

    def reload(self):

        return self.get_all()


profile_service = ProfileService()