from repositories.profile_telegram_repository import (
    profile_telegram_channel_repository,
)

from repositories.profile_mt5_repository import (
    profile_mt5_repository,
)

from core.trade_manager import trade_manager


class ProfileEngine:

    # ---------------------------------------------------------

    def process_signal(
        self,
        signal,
        chat_id,
    ):

        profiles = profile_telegram_channel_repository.get_profiles(
            chat_id
        )

        if not profiles:

            print("⚠️ No existen perfiles asociados a este canal.")

            return

        print(f"📂 Perfiles encontrados: {len(profiles)}")

        for profile in profiles:

            enabled = (
                profile.enabled
                if hasattr(profile, "enabled")
                else profile["enabled"]
            )

            if not enabled:

                continue

            self.process_profile(
                profile,
                signal,
            )

    # ---------------------------------------------------------

    def process_profile(
        self,
        profile,
        signal,
    ):

        accounts = profile_mt5_repository.get_accounts(
            profile.id if hasattr(profile, "id") else profile["id"]
        )

        if not accounts:

            name = (
                profile.name
                if hasattr(profile, "name")
                else profile["name"]
            )

            print(
                f"⚠️ El perfil '{name}' no tiene cuentas MT5."
            )

            return

        name = (
            profile.name
            if hasattr(profile, "name")
            else profile["name"]
        )

        print(f"🚀 Ejecutando perfil: {name}")

        for account in accounts:

            enabled = (
                account.enabled
                if hasattr(account, "enabled")
                else account["enabled"]
            )

            if not enabled:

                continue

            trade_manager.process_signal(

                signal,

                profile,

                account,

            )


profile_engine = ProfileEngine()
