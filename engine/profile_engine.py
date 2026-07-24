from core.event_bus import event_bus
from core.events import (
    ProfileStartedEvent,
    ProfileFinishedEvent,
    ExecutionStartedEvent,
    ExecutionFinishedEvent,
    ExecutionFailedEvent,
)


class ProfileEngine:

    def __init__(
        self,
        accounts_provider=None,
        execution_engine_instance=None,
    ):
        self._accounts_provider = accounts_provider
        self._execution_engine = execution_engine_instance

    def _get_accounts(self, profile_id):
        if self._accounts_provider is None:
            from repositories.profile_mt5_repository import (
                profile_mt5_repository,
            )
            self._accounts_provider = profile_mt5_repository.get_accounts

        return self._accounts_provider(profile_id)

    def _get_execution_engine(self):
        if self._execution_engine is None:
            from engine.execution_engine import execution_engine
            self._execution_engine = execution_engine

        return self._execution_engine

    def process_signal(self, signal, profile):
        """Aplica el contexto de un perfil y delega sus cuentas MT5."""

        event_bus.profileStarted.emit(
            ProfileStartedEvent(profile=profile, signal=signal)
        )

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
            return False

        signal.profile_id = profile.id
        signal.profile_name = profile.name
        signal.profile_telegram_account_id = getattr(
            profile,
            "telegram_account_id",
            None,
        )
        signal.execution_mode = getattr(
            profile,
            "execution_mode",
            None,
        )
        signal.tp_level = getattr(profile, "tp_level", 1)
        signal.execute_market = getattr(
            profile,
            "execute_market",
            True,
        )

        accounts = self._get_accounts(profile.id)
        enabled_accounts = [
            account
            for account in accounts
            if getattr(account, "enabled", True)
        ]

        if not enabled_accounts:
            event_bus.warning(
                f"{profile.name} no tiene cuentas MT5 activas."
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
            event_bus.executionStarted.emit(
                ExecutionStartedEvent(
                    profile=profile,
                    account=account,
                    signal=signal,
                )
            )

        try:
            success = self._get_execution_engine().execute_multiple(
                signal=signal,
                profile=profile,
                accounts=enabled_accounts,
            )
        except Exception as error:
            for account in enabled_accounts:
                event_bus.executionFailed.emit(
                    ExecutionFailedEvent(
                        profile=profile,
                        account=account,
                        signal=signal,
                        error=str(error),
                    )
                )

            event_bus.error(
                f"Error ejecutando perfil '{profile.name}': {error}"
            )
            success = False

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

        return success


profile_engine = ProfileEngine()
