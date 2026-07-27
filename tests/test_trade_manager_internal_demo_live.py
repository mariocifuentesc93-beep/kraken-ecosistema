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


def test_demo_splits_total_volume_into_multiple_mt5_orders(
    monkeypatch,
    profile_factory,
    account_factory,
):
    from mt5.executor import mt5_executor
    from risk.risk_manager import risk_manager
    from services.execution_preflight_service import (
        execution_preflight_service,
    )
    from trading.operation_manager import operation_manager

    profile = profile_factory(1, execution_mode="DEMO")
    account = account_factory(1)
    created = []
    opened = []

    def create(**_kwargs):
        operation = SimpleNamespace(id=len(created) + 1)
        created.append(operation)
        return operation

    monkeypatch.setattr(operation_manager, "create", create)
    monkeypatch.setattr(
        operation_manager,
        "open",
        lambda **kwargs: opened.append(kwargs),
    )
    monkeypatch.setattr(
        risk_manager,
        "validate",
        lambda **kwargs: (
            kwargs["signal"].metadata["position_sizing"].update(
                {
                    "allowed": True,
                    "volume": 4.5,
                    "order_volumes": (2.0, 2.0, 0.5),
                    "estimated_risk_money": 450.0,
                }
            )
            or (True, "Riesgo aprobado.")
        ),
    )
    monkeypatch.setattr(
        risk_manager,
        "calculate_lot",
        lambda **_kwargs: 4.5,
    )
    monkeypatch.setattr(
        execution_preflight_service,
        "validate",
        lambda **_kwargs: PreflightResult(True, "READY"),
    )
    sent = []
    monkeypatch.setattr(
        mt5_executor,
        "execute_market_order",
        lambda **kwargs: sent.append(kwargs["volume"])
        or SimpleNamespace(
            order=1000 + len(sent),
            deal=2000 + len(sent),
        ),
    )
    monkeypatch.setattr(
        TradeManager,
        "_log_preflight",
        lambda *args, **kwargs: None,
    )

    signal = _signal()
    result = TradeManager().process_signal(signal, profile, account)

    assert result is True
    assert sent == [2.0, 2.0, 0.5]
    assert len(created) == 3
    assert [item["volume"] for item in opened] == [2.0, 2.0, 0.5]
    assert signal.volume == 4.5
    assert signal.metadata["execution_plan"]["status"] == "FILLED"
    assert signal.metadata["execution_plan"]["completed_orders"] == 3


def test_demo_stops_remaining_orders_after_partial_send_failure(
    monkeypatch,
    profile_factory,
    account_factory,
):
    from mt5.executor import mt5_executor
    from risk.risk_manager import risk_manager
    from services.execution_preflight_service import (
        execution_preflight_service,
    )
    from trading.operation_manager import operation_manager

    profile = profile_factory(1, execution_mode="DEMO")
    account = account_factory(1)
    created = []
    closed = []
    monkeypatch.setattr(
        operation_manager,
        "create",
        lambda **_kwargs: created.append(
            SimpleNamespace(id=len(created) + 1)
        )
        or created[-1],
    )
    monkeypatch.setattr(operation_manager, "open", lambda **_kwargs: None)
    monkeypatch.setattr(
        operation_manager,
        "close",
        lambda **kwargs: closed.append(kwargs),
    )
    monkeypatch.setattr(
        risk_manager,
        "validate",
        lambda **kwargs: (
            kwargs["signal"].metadata["position_sizing"].update(
                {
                    "allowed": True,
                    "volume": 4.5,
                    "order_volumes": (2.0, 2.0, 0.5),
                }
            )
            or (True, "Riesgo aprobado.")
        ),
    )
    monkeypatch.setattr(
        risk_manager,
        "calculate_lot",
        lambda **_kwargs: 4.5,
    )
    monkeypatch.setattr(
        execution_preflight_service,
        "validate",
        lambda **_kwargs: PreflightResult(True, "READY"),
    )
    sent = []

    def execute(**kwargs):
        sent.append(kwargs["volume"])
        if len(sent) == 2:
            return None
        return SimpleNamespace(order=1001, deal=2001)

    monkeypatch.setattr(mt5_executor, "execute_market_order", execute)
    monkeypatch.setattr(
        TradeManager,
        "_log_preflight",
        lambda *args, **kwargs: None,
    )

    signal = _signal()
    result = TradeManager().process_signal(signal, profile, account)

    assert result is False
    assert sent == [2.0, 2.0]
    assert len(created) == 2
    assert len(closed) == 1
    assert signal.metadata["execution_plan"]["status"] == "PARTIAL"
    assert signal.metadata["execution_plan"]["completed_orders"] == 1
    assert signal.metadata["execution_plan"]["failed_order_index"] == 2
