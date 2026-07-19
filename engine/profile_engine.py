from engine.execution_engine import execution_engine

from repositories.profile_mt5_repository import (
    profile_mt5_repository,
)

from core.event_bus import event_bus

from core.events import (
    ProfileStartedEvent,
    ProfileFinishedEvent,
    ExecutionStartedEvent,
    ExecutionFinishedEvent,
    ExecutionFailedEvent,
)


class ProfileEngine:

    # ---------------------------------------------------------

    def process_signal(
        self,
        signal,
        profile,
    ):

        print()
        print("-" * 60)
        print(f"👤 PROFILE ENGINE -> {profile.name}")
        print("-" * 60)

        event_bus.profileStarted.emit(
            ProfileStartedEvent(
                profile=profile,
                signal=signal,
            )
        )

        # -----------------------------------------------------
        # VALIDAR PERFIL
        # -----------------------------------------------------

        if not getattr(profile, "enabled", True):

            event_bus.warning(
                f"Perfil '{profile.name}' deshabilitado."
            )

            event_bus.profileFinished.emit(
                ProfileFinishedEvent(
                    profile=profile,
                    signal=signal,
                    success=False,
                )
            )

            print(
                f"[ProfileEngine] Perfil '{profile.name}' deshabilitado."
            )

            return False

        # -----------------------------------------------------
        # CONTEXTO
        # -----------------------------------------------------

        signal.profile_id = profile.id
        signal.profile_name = profile.name

        if hasattr(profile, "telegram_account_id"):
            signal.profile_telegram_account_id = (
                profile.telegram_account_id
            )

        if hasattr(profile, "execution_mode"):
            signal.execution_mode = profile.execution_mode

        if hasattr(profile, "tp_level"):
            signal.tp_level = profile.tp_level

        if hasattr(profile, "execute_market"):
            signal.execute_market = profile.execute_market

        # -----------------------------------------------------
        # CUENTAS MT5
        # -----------------------------------------------------

        accounts = profile_mt5_repository.get_accounts(
            profile.id
        )

        if not accounts:

            event_bus.warning(
                f"{profile.name} no tiene cuentas MT5."
            )

            event_bus.profileFinished.emit(
                ProfileFinishedEvent(
                    profile=profile,
                    signal=signal,
                    success=False,
                )
            )

            print(
                f"[ProfileEngine] {profile.name} no tiene cuentas MT5."
            )

            return False

        enabled_accounts = [
            account
            for account in accounts
            if getattr(account, "enabled", True)
        ]

        if not enabled_accounts:

            event_bus.warning(
                f"{profile.name} no tiene cuentas activas."
            )

            event_bus.profileFinished.emit(
                ProfileFinishedEvent(
                    profile=profile,
                    signal=signal,
                    success=False,
                )
            )

            print(
                f"[ProfileEngine] {profile.name} no tiene cuentas MT5 activas."
            )

            return False

        print(f"Cuentas MT5 activas: {len(enabled_accounts)}")

        # -----------------------------------------------------
        # EJECUCIÓN
        # -----------------------------------------------------

        for account in enabled_accounts:

            event_bus.executionStarted.emit(
                ExecutionStartedEvent(
                    profile=profile,
                    account=account,
                    signal=signal,
                )
            )

        try:

            success = execution_engine.execute_multiple(
                signal=signal,
                profile=profile,
                accounts=enabled_accounts,
            )

        except Exception as e:

            for account in enabled_accounts:

                event_bus.executionFailed.emit(
                    ExecutionFailedEvent(
                        profile=profile,
                        account=account,
                        signal=signal,
                        error=str(e),
                    )
                )

            event_bus.error(
                f"Error ejecutando perfil '{profile.name}': {e}"
            )

            event_bus.profileFinished.emit(
                ProfileFinishedEvent(
                    profile=profile,
                    signal=signal,
                    success=False,
                )
            )

            return False

        for account in enabled_accounts:

            event_bus.executionFinished.emit(
                ExecutionFinishedEvent(
                    profile=profile,
                    account=account,
                    signal=signal,
                    success=success,
                )
            )

        event_bus.profileFinished.emit(
            ProfileFinishedEvent(
                profile=profile,
                signal=signal,
                success=success,
            )
        )

        if success:

            event_bus.log(
                f"Perfil '{profile.name}' ejecutado correctamente."
            )

        else:

            event_bus.warning(
                f"El perfil '{profile.name}' no pudo ejecutar la señal."
            )

        return success


profile_engine = ProfileEngine()