from types import SimpleNamespace

from models.mt5_account import MT5Account
from models.mt5_terminal import MT5Terminal
from mt5.executor import MT5Executor
from mt5.multi_terminal_connection import (
    MT5TerminalConnection,
    _invoke_mt5,
)
from risk.position_sizing_service import PositionSizingService
from risk.risk_manager import RiskManager
from services.mt5_connection_registry import (
    MT5ConnectionRegistryService,
)
from trading.operation_monitor import OperationMonitor


class FakeConnection:
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TIME_GTC = 0
    ORDER_FILLING_IOC = 1
    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_SLTP = 6
    TRADE_RETCODE_DONE = 10009
    DEAL_ENTRY_OUT = 1
    DEAL_ENTRY_OUT_BY = 3
    DEAL_REASON_SL = 4
    DEAL_REASON_TP = 5

    def __init__(self, account, terminal):
        self.account = account
        self.terminal = terminal
        self.login = account.login
        self.alive = True
        self.process_id = 1000 + int(terminal.id)
        self.closed = False
        self.requests = []
        self.positions = []

    def close(self):
        self.closed = True
        self.alive = False

    def terminal_info(self):
        return SimpleNamespace(connected=True, trade_allowed=True)

    def account_info(self):
        return SimpleNamespace(
            login=self.account.login,
            server=self.account.server,
            company="BridgeMarkets Ltd",
            trade_allowed=True,
            balance=10_000.0,
            equity=10_000.0,
            margin_free=9_000.0,
        )

    def symbol_info(self, name):
        return SimpleNamespace(
            name=name,
            visible=True,
            trade_mode=4,
            volume_min=0.01,
            volume_max=2.0,
            volume_step=0.01,
            trade_tick_size=0.01,
            trade_tick_value=1.0,
            point=0.001,
            trade_stops_level=0,
            trade_freeze_level=0,
        )

    def symbol_select(self, _name, _enabled):
        return True

    def symbol_info_tick(self, _name):
        return SimpleNamespace(ask=100.1, bid=100.0)

    def order_send(self, request):
        self.requests.append(dict(request))
        sequence = len(self.requests)
        return SimpleNamespace(
            retcode=self.TRADE_RETCODE_DONE,
            comment="done",
            order=(self.terminal.id * 10_000) + sequence,
            deal=(self.terminal.id * 20_000) + sequence,
            price=request["price"],
        )

    def last_error(self):
        return (1, "Success")

    def positions_get(self, **_kwargs):
        return list(self.positions)


def _account(account_id, terminal_id, login):
    return MT5Account(
        id=account_id,
        name=f"Account {account_id}",
        login=login,
        password="secret",
        server="BridgeMarkets-MT5",
        mt5_terminal_id=terminal_id,
        active=True,
    )


def _terminal(terminal_id):
    return MT5Terminal(
        id=terminal_id,
        name=f"Terminal {terminal_id}",
        executable_path=fr"C:\MT5-{terminal_id}\terminal64.exe",
        active=True,
        can_trade=True,
    )


def _registry():
    accounts = {
        1: _account(1, 11, 111111),
        2: _account(2, 22, 222222),
    }
    terminals = {11: _terminal(11), 22: _terminal(22)}
    created = []

    def factory(account, terminal):
        connection = FakeConnection(account, terminal)
        created.append(connection)
        return connection

    registry = MT5ConnectionRegistryService(
        account_provider=accounts.get,
        terminal_provider=terminals.get,
        connection_factory=factory,
    )
    return registry, accounts, terminals, created


def test_registry_keeps_one_isolated_worker_per_terminal_and_account():
    registry, _accounts, _terminals, created = _registry()

    first = registry.connection_for(1, 11)
    second = registry.connection_for(2, 22)

    assert first is registry.connection_for(1, 11)
    assert second is registry.connection_for(2, 22)
    assert first is not second
    assert first.login != second.login
    assert len(created) == 2

    registry.stop_all()
    assert first.closed is True
    assert second.closed is True
    assert registry.status() == {}


def test_terminal_proxy_sends_expanded_trade_request_fields():
    connection = object.__new__(MT5TerminalConnection)
    captured = {}

    def call(method, *args, **kwargs):
        captured.update(
            {"method": method, "args": args, "kwargs": kwargs}
        )
        return SimpleNamespace(
            retcode=connection.TRADE_RETCODE_DONE,
            order=110001,
            deal=210001,
            price=100.1,
        )

    connection.call = call
    request = {"action": connection.TRADE_ACTION_DEAL}

    connection.order_send(request)

    assert captured == {
        "method": "order_send",
        "args": (),
        "kwargs": request,
    }


def test_worker_unwraps_trade_request_into_native_named_call():
    calls = []

    class Api:
        def order_send(self, *args, **kwargs):
            calls.append((args, kwargs))
            return "sent"

    request = {"action": 1, "symbol": "LionX75"}

    result = _invoke_mt5(
        Api(),
        "order_send",
        (),
        {"request": request},
    )

    assert result == "sent"
    assert calls == [((), request)]


def test_executor_sends_each_account_to_its_own_terminal_worker():
    registry, accounts, _terminals, _created = _registry()
    executor = MT5Executor(connection_registry=registry)
    profile = SimpleNamespace(
        id=7,
        catalog_id="BRIDGE_SYNTHETICS",
        tp_level=2,
    )
    signal = SimpleNamespace(
        symbol="EMASVOL10",
        direction="BUY",
        stop_loss=99.0,
        take_profits=[101.0, 102.0, 103.0],
        metadata={},
    )
    preflight = SimpleNamespace(allowed=True)

    one = executor.execute_market_order(
        signal, 0.1, accounts[1], profile, preflight
    )
    two = executor.execute_market_order(
        signal, 0.2, accounts[2], profile, preflight
    )

    connection_one = registry.peek(1, 11)
    connection_two = registry.peek(2, 22)
    assert one.order == 110001
    assert two.order == 220001
    assert connection_one.requests[0]["volume"] == 0.1
    assert connection_two.requests[0]["volume"] == 0.2
    assert connection_one.requests[0]["tp"] == 102.0
    assert connection_two.requests[0]["tp"] == 102.0


def test_executor_retries_only_invalid_fill_with_supported_mode():
    registry, accounts, _terminals, _created = _registry()
    executor = MT5Executor(connection_registry=registry)
    connection = registry.connection_for(1, 11)
    connection.TRADE_RETCODE_INVALID_FILL = 10030
    connection.TRADE_RETCODE_PLACED = 10008
    connection.TRADE_RETCODE_DONE_PARTIAL = 10010
    connection.ORDER_FILLING_FOK = 0
    connection.ORDER_FILLING_RETURN = 2
    calls = []

    def order_send(request):
        calls.append(dict(request))
        if len(calls) == 1:
            return SimpleNamespace(
                retcode=10030,
                comment="Unsupported filling mode",
            )
        return SimpleNamespace(
            retcode=connection.TRADE_RETCODE_DONE,
            comment="Done",
            order=110002,
            deal=210002,
            price=100.1,
        )

    connection.order_send = order_send
    profile = SimpleNamespace(
        id=7,
        catalog_id="BRIDGE_SYNTHETICS",
        tp_level=2,
    )
    signal = SimpleNamespace(
        symbol="EMASVOL10",
        direction="BUY",
        stop_loss=99.0,
        take_profits=[101.0, 102.0, 103.0],
        metadata={},
    )

    result = executor.execute_market_order(
        signal,
        0.1,
        accounts[1],
        profile,
        SimpleNamespace(allowed=True),
    )

    assert result.order == 110002
    assert [call["type_filling"] for call in calls] == [1, 0]
    assert executor.last_error == ""


def test_risk_sizing_uses_metrics_and_symbol_from_destination_worker():
    registry, accounts, _terminals, _created = _registry()
    manager = RiskManager(
        sizing_service=PositionSizingService(),
        connection_registry=registry,
    )
    profile = SimpleNamespace(
        id=7,
        catalog_id="BRIDGE_SYNTHETICS",
        risk_enabled=True,
        risk_mode="AMOUNT",
        risk_amount=100.0,
        risk_percent=0.0,
        fixed_lot=0.0,
        max_risk_percent=10.0,
        min_lot=0.01,
        max_lot=100.0,
    )
    signal = SimpleNamespace(
        symbol="EMASVOL10",
        direction="BUY",
        entry=100.0,
        stop_loss=99.0,
        metadata={},
        volume=0.0,
    )

    approved, _reason = manager.validate(
        signal,
        profile=profile,
        account=accounts[2],
    )

    assert approved is True
    assert signal.metadata["position_sizing"]["mt5_account_id"] == 2
    assert signal.metadata["position_sizing"]["balance"] == 10_000.0
    assert registry.peek(2, 22) is not None
    assert registry.peek(1, 11) is None


class OperationRepo:
    def __init__(self, operations):
        self.operations = operations
        self.updated = []

    def get_open(self):
        return list(self.operations)

    def get_closed(self):
        return []

    def update(self, operation):
        self.updated.append(operation)


class Profiles:
    def get_by_id(self, _profile_id):
        return SimpleNamespace(
            execution_mode="DEMO",
            trailing_stop_enabled=False,
            tp1_management="NONE",
        )


class Milestones:
    def levels(self, operation):
        return {
            "TP1": operation.take_profit,
            "TP2": 0.0,
            "TP3": 0.0,
            "SL": operation.stop_loss,
        }

    def reached(self, _operation_id):
        return set()

    def record(self, *_args):
        return True


class Logs:
    def __init__(self):
        self.rows = []

    def info(self, module, message):
        self.rows.append(("INFO", module, message))

    def error(self, module, message):
        self.rows.append(("ERROR", module, message))


def test_operation_monitor_reads_each_ticket_from_its_account_worker():
    registry, _accounts, _terminals, _created = _registry()
    first = registry.connection_for(1, 11)
    second = registry.connection_for(2, 22)
    first.positions = [
        SimpleNamespace(
            ticket=101,
            profit=10.0,
            swap=0.0,
            price_current=101.0,
            sl=99.0,
            tp=102.0,
        )
    ]
    second.positions = [
        SimpleNamespace(
            ticket=202,
            profit=20.0,
            swap=0.0,
            price_current=102.0,
            sl=99.0,
            tp=103.0,
        )
    ]
    operations = [
        SimpleNamespace(
            id=1,
            profile_id=7,
            mt5_account_id=1,
            ticket=101,
            symbol="EMASVOL10",
            direction="BUY",
            take_profit=102.0,
            stop_loss=99.0,
            trailing_stop=False,
        ),
        SimpleNamespace(
            id=2,
            profile_id=7,
            mt5_account_id=2,
            ticket=202,
            symbol="EMASVOL10",
            direction="BUY",
            take_profit=103.0,
            stop_loss=99.0,
            trailing_stop=False,
        ),
    ]
    repository = OperationRepo(operations)
    monitor = OperationMonitor(
        operation_repo=repository,
        profile_repo=Profiles(),
        connection_registry=registry,
        logs=Logs(),
        milestone_repo=Milestones(),
    )

    monitor.update()

    assert operations[0].profit == 10.0
    assert operations[1].profit == 20.0
    assert len(repository.updated) == 2
