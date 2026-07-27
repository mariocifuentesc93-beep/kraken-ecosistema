from types import SimpleNamespace

import pytest

from core.trade_manager import TradeManager
from models.signal import Signal
from services.execution_preflight_service import PreflightResult


def _signal():
    signal = Signal(
        source="INTERNAL",
        external_signal_id="13785",
        symbol="LIONX150",
        direction="SELL",
        entry=301632.54,
        stop_loss=301705.49,
        take_profits=[301574.18, 301530.41, 301486.64],
    )
    signal.metadata["position_sizing"] = {
        "allowed": True,
        "volume": 0.10,
        "estimated_risk": 5.0,
    }
    return signal


@pytest.mark.parametrize("mode", ["DEMO", "LIVE"])
def test_internal_demo_and_live_reach_mt5_executor(
    monkeypatch,
    profile_factory,
    account_factory,
    mode,
):
    from mt5.executor import mt5_executor
    from risk.risk_manager import risk_manager
    from services.execution_preflight_service import (
        execution_preflight_service,
    )
    from trading.operation_manager import operation_manager

    profile = profile_factory(1, execution_mode=mode)
    account = account_factory(1)
    operation = SimpleNamespace(id=1)
    opened = []
    monkeypatch.setattr(
        operation_manager, "create", lambda **kwargs: operation
    )
    monkeypatch.setattr(
        operation_manager,
        "open",
        lambda **kwargs: opened.append(kwargs),
    )
    monkeypatch.setattr(
        risk_manager,
        "validate",
        lambda **kwargs: (True, "Riesgo aprobado."),
    )
    monkeypatch.setattr(
        risk_manager, "calculate_lot", lambda **kwargs: 0.10
    )
    monkeypatch.setattr(
        execution_preflight_service,
        "validate",
        lambda **kwargs: PreflightResult(
            True,
            "READY",
            details={"expected_login": 243274, "detected_login": 243274},
        ),
    )
    calls = []
    monkeypatch.setattr(
        mt5_executor,
        "execute_market_order",
        lambda **kwargs: calls.append(kwargs)
        or SimpleNamespace(order=12345, deal=67890),
    )
    monkeypatch.setattr(
        TradeManager, "_log_preflight", lambda *args, **kwargs: None
    )

    result = TradeManager().process_signal(
        _signal(), profile, account
    )

    assert result is True
    assert len(calls) == 1
    assert len(opened) == 1


def test_internal_risk_rejection_keeps_stage_and_reason(
    monkeypatch,
    profile_factory,
    account_factory,
):
    from risk.risk_manager import risk_manager
    from trading.operation_manager import operation_manager

    profile = profile_factory(1, execution_mode="DEMO")
    account = account_factory(1)
    operation = SimpleNamespace(id=1)
    rejected = []
    monkeypatch.setattr(
        operation_manager, "create", lambda **kwargs: operation
    )
    monkeypatch.setattr(
        operation_manager,
        "reject",
        lambda **kwargs: rejected.append(kwargs),
    )
    monkeypatch.setattr(
        risk_manager,
        "validate",
        lambda **kwargs: (False, "Cuenta MT5 incorrecta."),
    )
    monkeypatch.setattr(
        TradeManager, "_log_preflight", lambda *args, **kwargs: None
    )
    signal = _signal()

    result = TradeManager().process_signal(signal, profile, account)

    assert result is False
    assert len(rejected) == 1
    assert signal.execution_decision == "REJECTED"
    assert signal.rejection_reason == "Cuenta MT5 incorrecta."
    assert signal.metadata["failure_stage"] == "RISK"
