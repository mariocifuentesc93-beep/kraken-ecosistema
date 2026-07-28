from types import SimpleNamespace

import pytest

from models.operation import Operation
from trading.operation_monitor import OperationMonitor


class Operations:
    def __init__(self, operations, closed=None):
        self.operations = operations
        self.closed = closed or []
        self.updated = []

    def get_open(self):
        return self.operations

    def update(self, operation):
        self.updated.append(operation)

    def get_closed(self):
        return self.closed


class Profiles:
    def __init__(self, profile):
        self.profile = profile

    def get_by_id(self, _profile_id):
        return self.profile


class Executor:
    def __init__(self, succeeds=True):
        self.succeeds = succeeds
        self.calls = []

    def modify_position(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(retcode=1) if self.succeeds else None


class Logs:
    def __init__(self):
        self.rows = []

    def info(self, module, message):
        self.rows.append(("INFO", module, message))

    def error(self, module, message):
        self.rows.append(("ERROR", module, message))


class Milestones:
    def __init__(self, levels=None):
        self.events = set()
        self._levels = levels

    def levels(self, operation):
        if self._levels is not None:
            return dict(self._levels)
        return {"TP1": operation.take_profit, "TP2": 0.0, "TP3": 0.0, "SL": operation.stop_loss}

    def reached(self, _operation_id):
        return set(self.events)

    def record(self, _operation, milestone, _price, _mode):
        if milestone in self.events:
            return False
        self.events.add(milestone)
        return True


def subject(direction="BUY", price=110.0, enabled=True, succeeds=True):
    operation = Operation(
        id=7,
        profile_id=3,
        ticket=9001,
        symbol="LIONX40",
        direction=direction,
        stop_loss=90.0 if direction == "BUY" else 120.0,
        take_profit=105.0,
        status="OPEN",
    )
    position = SimpleNamespace(
        ticket=9001,
        price_current=price,
        sl=operation.stop_loss,
        tp=115.0 if direction == "BUY" else 95.0,
        profit=3.5,
        swap=0.0,
    )
    operations = Operations([operation])
    executor = Executor(succeeds)
    logs = Logs()
    monitor = OperationMonitor(
        operation_repo=operations,
        profile_repo=Profiles(
            SimpleNamespace(
                trailing_stop_enabled=enabled,
                tp1_management="PROTECT_TP1",
            )
        ),
        executor=executor,
        mt5_api=SimpleNamespace(positions_get=lambda: [position]),
        logs=logs,
        milestone_repo=Milestones(),
    )
    return monitor, operation, executor, logs


@pytest.mark.parametrize(
    ("direction", "price"),
    [("BUY", 105.0), ("SELL", 104.0)],
)
def test_reaching_tp1_moves_sl_to_tp1_and_preserves_final_tp(direction, price):
    monitor, operation, executor, logs = subject(direction, price)

    monitor.update()

    assert executor.calls == [
        {"ticket": 9001, "sl": 105.0, "tp": 115.0 if direction == "BUY" else 95.0}
    ]
    assert operation.stop_loss == 105.0
    assert operation.trailing_stop is True
    assert any("TP1_PROTECTED" in row[2] for row in logs.rows)


def test_tp1_protection_is_not_repeated_after_success():
    monitor, operation, executor, _logs = subject()
    monitor.update()
    monitor.update()

    assert len(executor.calls) == 1
    assert operation.trailing_stop is True


def test_does_not_modify_before_tp1_or_when_disabled():
    monitor, operation, executor, _logs = subject(price=104.99)
    monitor.update()
    assert executor.calls == []
    assert operation.trailing_stop is False

    monitor, operation, executor, _logs = subject(enabled=False)
    monitor.update()
    assert executor.calls == []
    assert operation.trailing_stop is False


def test_failed_modification_remains_pending_and_is_logged():
    monitor, operation, executor, logs = subject(succeeds=False)
    monitor.update()

    assert len(executor.calls) == 1
    assert operation.trailing_stop is False
    assert any("TP1_PROTECTION_FAILED" in row[2] for row in logs.rows)


def test_close_at_tp2_reconstructs_tp1_and_tp2_from_mt5_history():
    operation = Operation(
        id=8,
        profile_id=3,
        ticket=9002,
        symbol="LIONX40",
        direction="BUY",
        entry_price=100.0,
        stop_loss=90.0,
        take_profit=105.0,
        status="OPEN",
    )
    operations = Operations([operation])
    milestones = Milestones(
        {"TP1": 105.0, "TP2": 110.0, "TP3": 115.0, "SL": 90.0}
    )
    mt5_api = SimpleNamespace(
        positions_get=lambda: [],
        history_deals_get=lambda **_kwargs: [
            SimpleNamespace(
                entry=1,
                reason=7,
                price=110.0,
                profit=500.0,
                commission=0.0,
                swap=0.0,
            )
        ],
        DEAL_ENTRY_OUT=1,
        DEAL_ENTRY_OUT_BY=2,
        DEAL_REASON_TP=7,
        DEAL_REASON_SL=6,
    )
    logs = Logs()
    monitor = OperationMonitor(
        operation_repo=operations,
        profile_repo=Profiles(SimpleNamespace(execution_mode="DEMO")),
        executor=Executor(),
        mt5_api=mt5_api,
        logs=logs,
        milestone_repo=milestones,
    )

    monitor.update()

    assert operation.status == "CLOSED"
    assert operation.result == "WIN"
    assert operation.exit_price == 110.0
    assert operation.profit == 500.0
    assert milestones.events == {"TP1", "TP2"}
    assert any("reason=TP2_HIT" in row[2] for row in logs.rows)


def test_restart_recovers_ticket_already_protected_without_modifying_again():
    operation = Operation(
        id=9,
        profile_id=3,
        ticket=9003,
        symbol="LIONX40",
        direction="BUY",
        stop_loss=90.0,
        take_profit=105.0,
        status="OPEN",
        trailing_stop=False,
    )
    position = SimpleNamespace(
        ticket=9003,
        price_current=107.0,
        sl=105.0,
        tp=110.0,
        profit=25.0,
        swap=0.0,
    )
    operations = Operations([operation])
    executor = Executor()
    logs = Logs()
    milestones = Milestones(
        {"TP1": 105.0, "TP2": 110.0, "TP3": 0.0, "SL": 90.0}
    )
    monitor = OperationMonitor(
        operation_repo=operations,
        profile_repo=Profiles(
            SimpleNamespace(
                execution_mode="DEMO",
                trailing_stop_enabled=True,
                tp1_management="PROTECT_TP1",
            )
        ),
        executor=executor,
        mt5_api=SimpleNamespace(positions_get=lambda: [position]),
        logs=logs,
        milestone_repo=milestones,
    )

    monitor.recover_open_operations()
    monitor.recover_open_operations()

    assert executor.calls == []
    assert operation.trailing_stop is True
    assert operation.stop_loss == 105.0
    assert milestones.events == {"TP1"}
    assert sum("RECOVERED" in row[2] for row in logs.rows) == 2


def test_restart_restores_missing_tp1_protection_after_price_retraces():
    operation = Operation(
        id=10,
        profile_id=3,
        ticket=9004,
        symbol="LIONX40",
        direction="BUY",
        stop_loss=105.0,
        take_profit=105.0,
        status="OPEN",
        trailing_stop=True,
    )
    position = SimpleNamespace(
        ticket=9004,
        price_current=103.0,
        sl=90.0,
        tp=110.0,
        profit=5.0,
        swap=0.0,
    )
    operations = Operations([operation])
    executor = Executor()
    monitor = OperationMonitor(
        operation_repo=operations,
        profile_repo=Profiles(
            SimpleNamespace(
                execution_mode="DEMO",
                trailing_stop_enabled=True,
                tp1_management="PROTECT_TP1",
            )
        ),
        executor=executor,
        mt5_api=SimpleNamespace(positions_get=lambda: [position]),
        logs=Logs(),
        milestone_repo=Milestones(
            {"TP1": 105.0, "TP2": 110.0, "TP3": 0.0, "SL": 90.0}
        ),
    )

    monitor.recover_open_operations()

    assert executor.calls == [
        {"ticket": 9004, "sl": 105.0, "tp": 110.0}
    ]


def test_restart_backfills_tp2_for_already_closed_operation():
    operation = Operation(
        id=11,
        profile_id=3,
        ticket=9005,
        symbol="LIONX40",
        direction="SELL",
        entry_price=120.0,
        stop_loss=130.0,
        take_profit=115.0,
        status="CLOSED",
    )
    operations = Operations([], closed=[operation])
    milestones = Milestones(
        {"TP1": 115.0, "TP2": 110.0, "TP3": 105.0, "SL": 130.0}
    )
    mt5_api = SimpleNamespace(
        positions_get=lambda: [],
        history_deals_get=lambda **_kwargs: [
            SimpleNamespace(
                entry=1,
                reason=7,
                price=110.0,
                profit=420.0,
                commission=-1.0,
                swap=0.0,
            )
        ],
        DEAL_ENTRY_OUT=1,
        DEAL_ENTRY_OUT_BY=2,
        DEAL_REASON_TP=7,
        DEAL_REASON_SL=6,
    )
    logs = Logs()
    monitor = OperationMonitor(
        operation_repo=operations,
        profile_repo=Profiles(SimpleNamespace(execution_mode="DEMO")),
        executor=Executor(),
        mt5_api=mt5_api,
        logs=logs,
        milestone_repo=milestones,
    )

    monitor.recover_open_operations()
    monitor.recover_open_operations()

    assert milestones.events == {"TP1", "TP2"}
    assert operation.exit_price == 110.0
    assert operation.profit == 419.0
    assert operation.result == "WIN"
    assert len(operations.updated) == 1
    assert sum("MILESTONES_BACKFILLED" in row[2] for row in logs.rows) == 1


def test_recovery_remains_pending_until_mt5_is_connected():
    logs = Logs()
    monitor = OperationMonitor(
        operation_repo=Operations([]),
        profile_repo=Profiles(SimpleNamespace(execution_mode="DEMO")),
        executor=Executor(),
        mt5_api=SimpleNamespace(positions_get=lambda: None),
        logs=logs,
        milestone_repo=Milestones(),
    )

    assert monitor.recover_open_operations() is False
    assert any("RECOVERY_DEFERRED" in row[2] for row in logs.rows)
