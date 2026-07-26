from types import SimpleNamespace

import pytest

from services.execution_preflight_service import (
    ACCOUNT_DISCONNECTED,
    ACCOUNT_MISMATCH,
    BROKER_MISMATCH,
    EXECUTION_MODE_OFF,
    INSUFFICIENT_MARGIN,
    INVALID_SL,
    INVALID_TP,
    INVALID_VOLUME,
    MARKET_CLOSED,
    PROFILE_DISABLED,
    RISK_REJECTED,
    SYMBOL_DISABLED,
    SYMBOL_NOT_FOUND,
    ExecutionPreflightService,
    PreflightResult,
)


class FakeMT5:
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1

    def __init__(self):
        self.terminal = SimpleNamespace(connected=True, trade_allowed=True)
        self.account = SimpleNamespace(
            login=123,
            company="Bridge Markets",
            server="Bridge",
            trade_allowed=True,
            balance=10_000,
            equity=10_000,
            margin_free=8_000,
        )
        self.symbol = SimpleNamespace(
            visible=True,
            trade_mode=4,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            point=0.00001,
            trade_stops_level=10,
            trade_freeze_level=0,
        )
        self.tick = SimpleNamespace(ask=1.1001, bid=1.1000)
        self.margin = 100.0
        self.selected = True
        self.calls = []

    def terminal_info(self):
        self.calls.append("terminal_info")
        return self.terminal

    def account_info(self):
        self.calls.append("account_info")
        return self.account

    def symbol_info(self, _symbol):
        self.calls.append("symbol_info")
        return self.symbol

    def symbol_select(self, _symbol, _enabled):
        self.calls.append("symbol_select")
        return self.selected

    def symbol_info_tick(self, _symbol):
        self.calls.append("symbol_info_tick")
        return self.tick

    def order_calc_margin(self, *_args):
        self.calls.append("order_calc_margin")
        return self.margin


@pytest.fixture
def context():
    adapter = FakeMT5()
    terminal = SimpleNamespace(id=7, broker="Bridge Markets")
    service = ExecutionPreflightService(
        mt5_adapter=adapter,
        terminal_provider=lambda _terminal_id: terminal,
    )
    profile = SimpleNamespace(
        id=1, name="demo", active=True, enabled=True, execution_mode="DEMO"
    )
    account = SimpleNamespace(
        id=2, name="Cuenta DEMO", login=123, mt5_terminal_id=7
    )
    signal = SimpleNamespace(
        id=3,
        external_signal_id="100",
        symbol="EURUSD",
        direction="BUY",
        entry=1.1000,
        stop_loss=1.0900,
        take_profits=[1.1200],
        metadata={},
    )
    return service, adapter, profile, account, signal


def validate(context, **changes):
    service, adapter, profile, account, signal = context
    for target_name, values in changes.items():
        target = {
            "adapter": adapter,
            "profile": profile,
            "account": account,
            "signal": signal,
        }[target_name]
        for name, value in values.items():
            setattr(target, name, value)
    return service.validate(
        signal, profile, account, 0.10, {"allowed": True, "estimated_risk_money": 5}
    )


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"profile": {"enabled": False}}, PROFILE_DISABLED),
        ({"profile": {"execution_mode": "OFF"}}, EXECUTION_MODE_OFF),
        ({"signal": {"stop_loss": 1.1100}}, INVALID_SL),
        ({"signal": {"take_profits": [1.0900]}}, INVALID_TP),
        ({"adapter": {"terminal": None}}, ACCOUNT_DISCONNECTED),
        ({"adapter": {"account": SimpleNamespace(login=999)}}, ACCOUNT_MISMATCH),
        (
            {
                "adapter": {
                    "account": SimpleNamespace(
                        login=123,
                        company="Other Broker",
                        trade_allowed=True,
                        balance=10_000,
                        equity=10_000,
                        margin_free=8_000,
                    )
                }
            },
            BROKER_MISMATCH,
        ),
        ({"adapter": {"symbol": None}}, SYMBOL_NOT_FOUND),
        (
            {
                "adapter": {
                    "symbol": SimpleNamespace(visible=False),
                    "selected": False,
                }
            },
            SYMBOL_DISABLED,
        ),
    ],
)
def test_preflight_normalized_rejections(context, changes, code):
    assert validate(context, **changes).code == code


def test_preflight_rejects_risk(context):
    service, _, profile, account, signal = context
    result = service.validate(
        signal, profile, account, 0.10, {"allowed": False, "reason": "cap"}
    )
    assert result.code == RISK_REJECTED


def test_preflight_rejects_invalid_volume(context):
    service, _, profile, account, signal = context
    result = service.validate(
        signal, profile, account, 0, {"allowed": True}
    )
    assert result.code == INVALID_VOLUME


def test_preflight_rejects_closed_market(context):
    service, adapter, profile, account, signal = context
    adapter.symbol.trade_mode = 0
    result = service.validate(
        signal, profile, account, 0.10, {"allowed": True}
    )
    assert result.code == MARKET_CLOSED


def test_preflight_rejects_insufficient_margin(context):
    service, adapter, profile, account, signal = context
    adapter.margin = 20_000
    result = service.validate(
        signal, profile, account, 0.10, {"allowed": True}
    )
    assert result.code == INSUFFICIENT_MARGIN


def test_preflight_ready(context):
    result = validate(context)
    assert result.allowed is True
    assert result.state == "READY"


def test_simulation_never_queries_mt5(context):
    service, adapter, profile, account, signal = context
    profile.execution_mode = "SIMULATION"
    result = service.validate(
        signal, profile, account, 0.10, {"allowed": True}
    )
    assert result.allowed is True
    assert adapter.calls == []


def test_executor_does_not_send_when_preflight_blocks(monkeypatch):
    from mt5 import executor as executor_module

    monkeypatch.setattr(
        executor_module.mt5,
        "order_send",
        lambda _request: pytest.fail("order_send must not be called"),
    )
    result = executor_module.MT5Executor().execute_market_order(
        signal=SimpleNamespace(metadata={}),
        volume=0.1,
        account=SimpleNamespace(),
        preflight_result=PreflightResult(
            False, "BLOCKED", ACCOUNT_MISMATCH, "mismatch"
        ),
    )
    assert result is None
