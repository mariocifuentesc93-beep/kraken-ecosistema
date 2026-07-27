import sys

import pytest

from engine.execution_engine import ExecutionEngine
from engine.profile_engine import ProfileEngine
from models.signal import Signal


class FakeTradeManager:
    def __init__(self):
        self.calls = []

    def reload(self):
        return None

    def process_signal(self, signal, profile, account):
        self.calls.append((signal, profile, account))
        return True


def internal_signal():
    return Signal(
        source="INTERNAL",
        external_signal_id="12304",
        symbol="EmasVol20",
        direction="BUY",
        entry=100,
        stop_loss=90,
        take_profits=[110, 120, 130],
    )


def pipeline(profile, account):
    manager = FakeTradeManager()
    execution = ExecutionEngine(manager)
    execution.start()
    profile_engine = ProfileEngine(
        accounts_provider=lambda profile_id: [account],
        execution_engine_instance=execution,
    )
    return manager, profile_engine


def test_internal_simulation_reaches_fake_trade_manager(
    profile_factory,
    account_factory,
):
    profile = profile_factory(
        1,
        signal_source_mode="INTERNAL",
        execution_mode="SIMULATION",
    )
    account = account_factory(1)
    account.execution_mode = "LIVE"
    manager, profile_engine = pipeline(profile, account)

    assert profile_engine.process_signal(internal_signal(), profile) is True
    assert len(manager.calls) == 1
    assert manager.calls[0][0].execution_mode == "SIMULATION"
    assert "MetaTrader5" not in sys.modules


def test_internal_demo_reaches_trade_manager_and_keeps_profile_mode(
    profile_factory,
    account_factory,
):
    profile = profile_factory(
        1,
        signal_source_mode="INTERNAL",
        execution_mode="DEMO",
    )
    manager, profile_engine = pipeline(
        profile,
        account_factory(1),
    )

    assert profile_engine.process_signal(internal_signal(), profile) is True
    assert len(manager.calls) == 1
    assert manager.calls[0][0].execution_mode == "DEMO"
    assert "MetaTrader5" not in sys.modules


def test_internal_live_reaches_trade_manager_and_keeps_profile_mode(
    profile_factory,
    account_factory,
):
    profile = profile_factory(
        1,
        signal_source_mode="INTERNAL",
        execution_mode="LIVE",
    )
    manager, profile_engine = pipeline(profile, account_factory(1))

    assert profile_engine.process_signal(internal_signal(), profile) is True
    assert len(manager.calls) == 1
    assert manager.calls[0][0].execution_mode == "LIVE"
    assert "MetaTrader5" not in sys.modules
