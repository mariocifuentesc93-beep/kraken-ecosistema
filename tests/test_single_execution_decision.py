from types import SimpleNamespace

from engine.execution_engine import ExecutionEngine
from models.signal import Signal


class DecisionManager:
    def __init__(self):
        self.calls = []

    def process_signal(self, signal, profile, account):
        self.calls.append((signal, profile, account))
        return True


def context(mode="SIMULATION", source="TELEGRAM"):
    signal = Signal(
        source=source,
        symbol="EMASVOL20",
        direction="BUY",
        entry=100,
        stop_loss=90,
        take_profits=[110, 120, 130],
    )
    profile = SimpleNamespace(id=1, name="P", execution_mode=mode)
    account = SimpleNamespace(id=2, name="A", enabled=True)
    return signal, profile, account


def test_one_signal_produces_at_most_one_mode_decision():
    manager = DecisionManager()
    engine = ExecutionEngine(manager)
    engine.start()
    signal, profile, account = context()
    assert engine.execute(signal, profile, account) is True
    assert len(manager.calls) == 1


def test_internal_demo_and_live_never_reach_decision_manager():
    for mode in ("DEMO", "LIVE", "PAPER"):
        manager = DecisionManager()
        engine = ExecutionEngine(manager)
        engine.start()
        signal, profile, account = context(mode, "INTERNAL")
        assert engine.execute(signal, profile, account) is False
        assert manager.calls == []

