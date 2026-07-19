from trading.execution_pipeline import execution_pipeline


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
            execution_pipeline.simulate(signal, profile, account, "tp3")
            return True
        # LIVE remains intentionally non-executable in this phase.
        execution_pipeline.create(signal, profile, account, mode)
        return False

    def execute_multiple(self, signal, profile, accounts):
        return any(self.execute(signal, profile, account) for account in accounts)


execution_engine = ExecutionEngine()
