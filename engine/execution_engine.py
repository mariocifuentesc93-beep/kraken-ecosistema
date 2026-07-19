from trading.execution_pipeline import execution_pipeline
from trading.paper_trading_engine import paper_trading_engine


class ExecutionEngine:
    """Simulation-first execution engine; it never submits a LIVE MT5 order."""

    def __init__(self):
        self.running = False

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def execute(self, signal, profile, account):
        if not self.running:
            return False
        mode = getattr(profile, "execution_mode", "OFF")
        if mode == "SIMULATION":
            execution_pipeline.simulate_with_market_data(signal, profile, account)
            return True
        if mode == "PAPER":
            return paper_trading_engine.execute(signal, profile, account) is not None
        # LIVE remains intentionally non-executable in this phase.
        operation = execution_pipeline.create(signal, profile, account, "LIVE_BLOCKED")
        execution_pipeline.transition(
            operation, "REJECTED", "La ejecución LIVE permanece bloqueada.", "LIVE_BLOCKED"
        )
        return False

    def execute_multiple(self, signal, profile, accounts):
        return any(self.execute(signal, profile, account) for account in accounts)


execution_engine = ExecutionEngine()
