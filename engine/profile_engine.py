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
        default_account_provider=None,
        execution_engine_instance=None,
    ):
        self._accounts_provider = accounts_provider
        self._default_account_provider = default_account_provider
        self._execution_engine = execution_engine_instance

    def _get_accounts(self, profile_id):
        if self._accounts_provider is None:
            from repositories.profile_mt5_repository import (
                profile_mt5_repository,
            )
            self._accounts_provider = profile_mt5_repository.get_accounts

        return self._accounts_provider(profile_id)

    def _get_default_account(self, account_id):
        if account_id is None:
            return None
        if self._default_account_provider is None:
            from repositories.mt5_account_repository import (
                mt5_account_repository,
            )
            self._default_account_provider = mt5_account_repository.get_by_id
        return self._default_account_provider(account_id)

    @staticmethod
    def _reject(signal, stage, reason):
        signal.rejection_reason = reason
        signal.execution_decision = "REJECTED"
        signal.metadata["failure_stage"] = stage
        signal.metadata["rejection_reason"] = reason
        signal.metadata["execution_decision"] = "REJECTED"
        return False

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
            reason = f"Perfil '{profile.name}' deshabilitado."
            self._reject(signal, "PROFILE", reason)
            event_bus.warning(reason)
            event_bus.profileFinished.emit(
                ProfileFinishedEvent(
                    profile=profile,
                    signal=signal,
                    success=False,
                )
            )
            return False

        if getattr(signal, "source", "") == "INTERNAL":
            from engine.execution_engine import internal_execution_allowed

            if not internal_execution_allowed(profile):
                mode = getattr(profile, "execution_mode", None)
                reason = (
                    f"Perfil '{profile.name}' bloqueó INTERNAL: "
                    f"execution_mode={mode} no está permitido."
                )
                self._reject(signal, "EXECUTION_MODE", reason)
                event_bus.warning(reason)
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
        if not accounts:
            default_account = self._get_default_account(
                getattr(profile, "default_mt5_account", None)
            )
            if default_account is not None:
                accounts = [default_account]
        enabled_accounts = [
            account
            for account in accounts
            if getattr(account, "enabled", True)
        ]

        if not enabled_accounts:
            reason = (
                f"{profile.name} no tiene cuentas MT5 activas ni una "
                "cuenta predeterminada válida."
            )
            self._reject(signal, "PROFILE_ACCOUNT", reason)
            event_bus.warning(
                reason
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
            import traceback

            reason = f"Error ejecutando perfil '{profile.name}': {error}"
            self._reject(signal, "EXECUTION", reason)
            signal.metadata["traceback"] = traceback.format_exc()
            for account in enabled_accounts:
                event_bus.executionFailed.emit(
                    ExecutionFailedEvent(
                        profile=profile,
                        account=account,
                        signal=signal,
                        error=str(error),
                    ),
                    str(error),
                )

            event_bus.error(reason)
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

        if success:
            signal.rejection_reason = ""
            signal.execution_decision = (
                "SIMULATED"
                if str(getattr(profile, "execution_mode", "")).upper()
                == "SIMULATION"
                else "EXECUTED"
            )
            signal.metadata["execution_decision"] = signal.execution_decision
            signal.metadata["execution_mode"] = getattr(
                profile, "execution_mode", ""
            )

        return success


profile_engine = ProfileEngine()
