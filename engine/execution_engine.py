from copy import deepcopy

# INTERNAL may execute in DEMO or LIVE only after the same risk and pre-flight
# gates used by every other source.
INTERNAL_SAFE_EXECUTION_MODES = {"OFF", "SIMULATION", "DEMO", "LIVE"}


def execution_mode_value(value):
    return str(getattr(value, "value", value) or "").strip().upper()


def internal_execution_allowed(profile) -> bool:
    return execution_mode_value(
        getattr(profile, "execution_mode", None)
    ) in INTERNAL_SAFE_EXECUTION_MODES


class ExecutionEngine:
    """Simulation-first execution engine; it never submits a LIVE MT5 order."""

    def __init__(self, trade_manager_instance=None):
        self.running = False
        self._trade_manager = trade_manager_instance

    def start(self):
        self.running = True
        if self._trade_manager is not None and hasattr(
            self._trade_manager, "reload"
        ):
            self._trade_manager.reload()

    def stop(self):
        self.running = False

    def _get_trade_manager(self):
        if self._trade_manager is None:
            from core.trade_manager import trade_manager
            self._trade_manager = trade_manager
        return self._trade_manager

    def execute(self, signal, profile, account):
        if not self.running:
            return False

        mode = execution_mode_value(
            getattr(profile, "execution_mode", "OFF")
        )
        if getattr(signal, "source", "") == "INTERNAL":
            if mode not in INTERNAL_SAFE_EXECUTION_MODES:
                return False
            if mode == "OFF":
                return False

        account_signal = deepcopy(signal)
        account_signal.profile_id = profile.id
        account_signal.profile_name = profile.name
        account_signal.mt5_account_id = account.id
        account_signal.mt5_account_name = account.name
        account_signal.execution_mode = mode

        for field, default in (
            ("risk_mode", None),
            ("risk_percent", 0.0),
            ("risk_amount", 0.0),
            ("fixed_lot", 0.0),
            ("comment", ""),
            ("deviation", 20),
        ):
            setattr(account_signal, field, getattr(account, field, default))
        account_signal.magic = getattr(account, "magic_number", 0)

        result = self._get_trade_manager().process_signal(
            signal=account_signal,
            profile=profile,
            account=account,
        )
        if not result:
            signal.rejection_reason = account_signal.rejection_reason
            signal.execution_decision = account_signal.execution_decision
            for key in (
                "failure_stage",
                "rejection_reason",
                "execution_decision",
                "position_sizing",
                "execution_preflight",
            ):
                if key in account_signal.metadata:
                    signal.metadata[key] = account_signal.metadata[key]
        return result

        if mode == "SIMULATION":
            execution_pipeline.simulate_with_market_data(
                account_signal, profile, account
            )
            return True
        if mode == "PAPER":
            from trading.paper_trading_engine import paper_trading_engine

            return (
                paper_trading_engine.execute(
                    account_signal, profile, account
                )
                is not None
            )
        # LIVE remains intentionally non-executable in this phase.
        operation = execution_pipeline.create(
            account_signal, profile, account, "LIVE_BLOCKED"
        )
        execution_pipeline.transition(
            operation, "REJECTED", "La ejecución LIVE permanece bloqueada.", "LIVE_BLOCKED"
        )
        return False

    def execute_multiple(self, signal, profile, accounts):
        success = False
        for account in accounts:
            if not getattr(account, "enabled", True):
                continue
            if self.execute(signal, profile, account):
                success = True
        return success


execution_engine = ExecutionEngine()
