from types import SimpleNamespace
import sqlite3

import pytest

from database.profile_risk_migration import downgrade, upgrade
from risk.position_sizing_service import (
    PositionSizingError,
    PositionSizingService,
)
from risk.risk_manager import RiskManager


def profile(mode="PERCENT", **values):
    defaults = dict(
        risk_enabled=True,
        risk_mode=mode,
        risk_percent=2.0,
        max_risk_percent=5.0,
        risk_amount=100.0,
        fixed_lot=0.10,
        min_lot=0.01,
        max_lot=100.0,
    )
    defaults.update(values)
    return SimpleNamespace(**defaults)


def account(balance=10_000, equity=10_000, account_id=1):
    return SimpleNamespace(
        id=account_id, balance=balance, equity=equity, login=account_id
    )


def spec(**values):
    defaults = dict(
        trade_tick_size=0.01,
        trade_tick_value=1.0,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01,
    )
    defaults.update(values)
    return SimpleNamespace(**defaults)


def calculate(selected_profile=None, selected_account=None, selected_spec=None):
    return PositionSizingService().calculate(
        selected_profile or profile(),
        selected_account or account(),
        "TEST",
        "BUY",
        100.0,
        99.0,
        selected_spec or spec(),
    )


def test_percent_uses_destination_account_balance():
    small = calculate(selected_account=account(1_000, 1_000, 1))
    large = calculate(selected_account=account(10_000, 10_000, 2))
    assert small.volume == 0.2
    assert large.volume == 2.0


def test_amount_and_fixed_lot_modes():
    assert calculate(profile("AMOUNT", risk_amount=50)).volume == 0.5
    assert calculate(profile("LOT", fixed_lot=0.37)).volume == 0.37


@pytest.mark.parametrize("value", [0, -1])
def test_invalid_percent_is_rejected(value):
    with pytest.raises(PositionSizingError, match="risk_percent"):
        calculate(profile(risk_percent=value))


def test_percent_cannot_exceed_profile_maximum():
    with pytest.raises(PositionSizingError, match="supera"):
        calculate(profile(risk_percent=6, max_risk_percent=5))


@pytest.mark.parametrize(
    ("selected_profile", "message"),
    [
        (profile("AMOUNT", risk_amount=0), "risk_amount"),
        (profile("LOT", fixed_lot=0), "fixed_lot"),
    ],
)
def test_invalid_amount_or_lot_is_rejected(selected_profile, message):
    with pytest.raises(PositionSizingError, match=message):
        calculate(selected_profile)


def test_volume_is_floored_to_step_and_never_rounded_up():
    result = calculate(
        profile("AMOUNT", risk_amount=37),
        selected_spec=spec(volume_step=0.1),
    )
    assert result.raw_volume == 0.37
    assert result.volume == 0.3
    assert result.estimated_risk_money <= 37


def test_below_minimum_is_rejected_instead_of_forced_up():
    with pytest.raises(PositionSizingError, match="debajo del mínimo"):
        calculate(
            profile("AMOUNT", risk_amount=1),
            selected_spec=spec(volume_min=0.1, volume_step=0.1),
        )


def test_volume_respects_maximum():
    result = calculate(
        profile("AMOUNT", risk_amount=500, max_risk_percent=5, max_lot=1),
    )
    assert result.volume == 1


def test_volume_is_split_across_broker_maximum_without_multiplying_risk():
    result = calculate(
        profile("AMOUNT", risk_amount=450, max_risk_percent=5),
        selected_spec=spec(volume_max=2),
    )

    assert result.volume == 4.5
    assert result.order_volumes == (2.0, 2.0, 0.5)
    assert result.order_count == 3
    assert result.estimated_risk_money == 450


def test_execution_plan_allows_at_most_ten_orders():
    result = calculate(
        profile("AMOUNT", risk_amount=200, max_risk_percent=5),
        selected_spec=spec(
            trade_tick_value=0.1,
            volume_max=2,
        ),
    )
    assert result.order_count == 10
    assert result.order_volumes == (2.0,) * 10

    with pytest.raises(PositionSizingError, match="más de 10 órdenes"):
        calculate(
            profile("AMOUNT", risk_amount=201, max_risk_percent=5),
            selected_spec=spec(
                trade_tick_value=0.1,
                volume_max=2,
            ),
        )


@pytest.mark.parametrize(
    ("entry", "stop", "selected_spec", "message"),
    [
        (100, 0, spec(), "Stop Loss"),
        (100, 100, spec(), "distancia"),
        (100, 99, spec(trade_tick_value=0), "tick_value"),
        (100, 99, spec(trade_tick_size=0), "tick_size"),
    ],
)
def test_missing_market_inputs_are_rejected(entry, stop, selected_spec, message):
    with pytest.raises(PositionSizingError, match=message):
        PositionSizingService().calculate(
            profile(), account(), "TEST", "BUY", entry, stop, selected_spec
        )


def test_two_profiles_can_size_same_signal_differently():
    one = calculate(profile(risk_percent=1))
    two = calculate(profile(risk_percent=2))
    assert one.volume == 1
    assert two.volume == 2


def test_profile_risk_migration_is_idempotent_and_reversible():
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE profiles(id INTEGER PRIMARY KEY, name TEXT)")
    db.execute("INSERT INTO profiles(name) VALUES ('demo')")
    db.commit()
    upgrade(db)
    upgrade(db)
    assert [row[1] for row in db.execute("PRAGMA table_info(profiles)")].count(
        "max_risk_percent"
    ) == 1
    assert db.execute("SELECT name FROM profiles").fetchone()[0] == "demo"
    downgrade(db)
    assert "max_risk_percent" not in {
        row[1] for row in db.execute("PRAGMA table_info(profiles)")
    }
    assert db.execute("SELECT name FROM profiles").fetchone()[0] == "demo"


def test_risk_manager_uses_injected_destination_context_without_mt5():
    manager = RiskManager(
        sizing_service=PositionSizingService(),
        symbol_info_provider=lambda destination, symbol: spec(),
    )
    signal = SimpleNamespace(
        symbol="TEST", direction="BUY", entry=100.0, stop_loss=99.0,
        metadata={}, volume=0.0,
    )
    destination = account(10_000, 10_000, 77)
    selected_profile = profile(risk_percent=1)

    approved, _message = manager.validate(
        signal, account=destination, profile=selected_profile
    )

    assert approved is True
    assert signal.volume == 1.0
    assert signal.metadata["position_sizing"]["balance"] == 10_000


def test_risk_manager_resolves_canonical_symbol_to_mt5_name(monkeypatch):
    import MetaTrader5 as mt5
    from mt5.connector import mt5_connector

    monkeypatch.setattr(mt5_connector, "current_account", 243274)
    requested = []
    monkeypatch.setattr(
        mt5_connector,
        "get_symbol_info",
        lambda symbol: requested.append(symbol) or spec(),
    )
    monkeypatch.setattr(
        mt5_connector,
        "get_tick",
        lambda _symbol: SimpleNamespace(ask=138170.49, bid=138170.59),
    )
    monkeypatch.setattr(
        mt5,
        "order_calc_profit",
        lambda _kind, _symbol, volume, entry, stop: (
            stop - entry
        ) * volume,
    )
    manager = RiskManager(sizing_service=PositionSizingService())
    signal = SimpleNamespace(
        symbol="EMASVOL50",
        direction="SELL",
        entry=138170.59,
        stop_loss=138192.96,
        metadata={},
        volume=0.0,
    )

    approved, _message = manager.validate(
        signal,
        account=account(10_000, 10_000, 243274),
        profile=profile(risk_percent=1),
    )

    assert approved is True, _message
    assert requested == ["EmasVol50"]


def test_risk_manager_refreshes_destination_metrics_from_connected_mt5(
    monkeypatch,
):
    import MetaTrader5 as mt5
    from mt5.connector import mt5_connector

    monkeypatch.setattr(mt5_connector, "current_account", 243274)
    monkeypatch.setattr(
        mt5_connector,
        "get_account_info",
        lambda: SimpleNamespace(
            login=243274,
            balance=9995.60,
            equity=9995.60,
            margin_free=9500.0,
        ),
    )
    monkeypatch.setattr(
        mt5_connector,
        "get_symbol_info",
        lambda _symbol: spec(),
    )
    monkeypatch.setattr(
        mt5_connector,
        "get_tick",
        lambda _symbol: SimpleNamespace(ask=269699.69, bid=269699.79),
    )
    monkeypatch.setattr(
        mt5,
        "order_calc_profit",
        lambda _kind, _symbol, volume, entry, stop: (
            stop - entry
        ) * volume,
    )
    destination = account(0, 0, 243274)
    manager = RiskManager(sizing_service=PositionSizingService())
    signal = SimpleNamespace(
        symbol="LIONX120",
        direction="SELL",
        entry=269699.79,
        stop_loss=269771.67,
        metadata={},
        volume=0.0,
    )

    approved, _message = manager.validate(
        signal,
        account=destination,
        profile=profile(risk_percent=1),
    )

    assert approved is True
    assert destination.balance == 9995.60
    assert destination.equity == 9995.60
    assert destination.free_margin == 9500.0
    assert signal.metadata["position_sizing"]["balance"] == 9995.60


def test_risk_rejection_is_controlled_and_does_not_create_default_lot():
    manager = RiskManager(
        sizing_service=PositionSizingService(),
        symbol_info_provider=lambda destination, symbol: spec(),
    )
    signal = SimpleNamespace(
        symbol="TEST", direction="BUY", entry=100.0, stop_loss=0.0,
        metadata={}, volume=0.0,
    )
    approved, reason = manager.validate(
        signal, account=account(), profile=profile()
    )
    assert approved is False
    assert "Stop Loss" in reason
    assert signal.volume == 0.0
    assert signal.metadata["position_sizing"]["allowed"] is False
