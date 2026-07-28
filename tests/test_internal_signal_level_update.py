from types import SimpleNamespace

from internal.signal_level_update import InternalSignalLevelUpdate
from models.operation import Operation
from models.signal import Signal
from services.internal_signal_level_update_service import (
    InternalSignalLevelUpdateService,
)


def test_update_targets_only_exact_open_signal_and_profile_tp_level():
    signal = Signal(
        id=10, source="INTERNAL", external_signal_id="77",
        symbol="EmasVol20", direction="BUY", entry=100,
        stop_loss=90, take_profits=[110, 120, 130],
    )
    operation = Operation(
        id=21, signal_id=10, profile_id=3, mt5_account_id=4,
        ticket=900, symbol="EMASVOL20", direction="BUY",
        stop_loss=90, take_profit=110, status="OPEN",
    )

    class Signals:
        def get_by_idempotency_key(self, key):
            assert key == "INTERNAL:EMASVOL20:77"
            return signal

        def update_levels(self, *args):
            self.saved = args

    class Operations:
        def get_open_by_signal(self, signal_id):
            assert signal_id == 10
            return [operation]

        def update(self, value):
            self.saved = value

    class Profiles:
        def get_by_id(self, profile_id):
            return SimpleNamespace(
                id=profile_id, tp_level=2, execution_mode="LIVE"
            )

    class Api:
        def positions_get(self, ticket):
            return [
                SimpleNamespace(
                    ticket=ticket, symbol="emasvol20", price_current=105
                )
            ]

        def symbol_info(self, symbol):
            return SimpleNamespace(
                point=0.01, trade_stops_level=5, trade_freeze_level=0
            )

    class Connections:
        def connection_for(self, account_id, terminal_id):
            return Api()

    class Executor:
        last_error = ""

        def modify_position(self, **kwargs):
            self.kwargs = kwargs
            return SimpleNamespace(retcode=10009)

    class Milestones:
        def update_levels(self, *args):
            self.saved = args

    class Logs:
        def info(self, *args):
            pass

        def error(self, *args):
            raise AssertionError(args)

    executor = Executor()
    operations = Operations()
    signals = Signals()
    service = InternalSignalLevelUpdateService(
        signals, operations, Profiles(), Milestones(), executor,
        Connections(), Logs(),
    )
    update = InternalSignalLevelUpdate(
        "EMASVOL20", "77", "BUY", 90, 95,
        (110, 120, 130), (112, 122, 132),
        signal.received_at,
    )

    result = service.apply(update)

    assert result.updated == [21]
    assert result.failed == []
    assert executor.kwargs == {
        "ticket": 900,
        "sl": 95.0,
        "tp": 122.0,
        "mt5_account_id": 4,
    }
    assert operation.stop_loss == 95
    assert operation.take_profit == 112
    assert signals.saved[0:3] == (10, 95.0, [112, 122, 132])


def test_update_rejects_levels_on_wrong_side_without_mt5_change():
    signal = Signal(
        id=10, source="INTERNAL", external_signal_id="77",
        symbol="EmasVol20", direction="BUY", entry=100,
        stop_loss=90, take_profits=[110, 120, 130],
    )
    operation = Operation(
        id=21, signal_id=10, profile_id=3, mt5_account_id=4,
        ticket=900, symbol="EMASVOL20", direction="BUY", status="OPEN",
    )
    repository = SimpleNamespace(
        get_by_idempotency_key=lambda key: signal,
        update_levels=lambda *args: None,
    )
    operations = SimpleNamespace(
        get_open_by_signal=lambda signal_id: [operation],
        update=lambda value: None,
    )
    profile = SimpleNamespace(tp_level=2, execution_mode="LIVE")
    api = SimpleNamespace(
        positions_get=lambda ticket: [
            SimpleNamespace(symbol="emasvol20", price_current=105)
        ],
        symbol_info=lambda symbol: SimpleNamespace(
            point=0.01, trade_stops_level=0, trade_freeze_level=0
        ),
    )

    class Executor:
        def modify_position(self, **kwargs):
            raise AssertionError("No debe modificar MT5")

    logs = SimpleNamespace(info=lambda *args: None, error=lambda *args: None)
    service = InternalSignalLevelUpdateService(
        repository, operations,
        SimpleNamespace(get_by_id=lambda value: profile),
        SimpleNamespace(update_levels=lambda *args: None),
        Executor(),
        SimpleNamespace(connection_for=lambda *args: api),
        logs,
    )
    update = InternalSignalLevelUpdate(
        "EMASVOL20", "77", "BUY", 90, 106,
        (110, 120, 130), (112, 122, 132),
        signal.received_at,
    )

    result = service.apply(update)

    assert result.updated == []
    assert len(result.failed) == 1
