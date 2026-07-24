import asyncio
import sys
from types import SimpleNamespace

from engine.execution_engine import ExecutionEngine
from engine.kraken_engine import KrakenEngine
from engine.profile_engine import ProfileEngine
from engine.signal_engine import SignalEngine
from telegram.listener import register_telegram_listener


class FakeTradeManager:
    def __init__(self):
        self.received = []
        self.reloaded = False

    def reload(self):
        self.reloaded = True

    def process_signal(self, signal, profile, account):
        self.received.append((signal, profile, account))
        return True


class FakeOperationMonitor:
    def __init__(self):
        self.running = False

    def start(self):
        self.running = True

    def stop(self):
        self.running = False


class FakeTelegramClient:
    def __init__(self):
        self.handler = None

    def on(self, _event):
        def decorator(handler):
            self.handler = handler
            return handler

        return decorator


def test_valid_telegram_signal_reaches_fake_trade_manager(
    profile_factory,
    account_factory,
):
    profile = profile_factory(1, "Telegram profile")
    account = account_factory(10, "Simulation account")
    trade_manager = FakeTradeManager()
    operation_monitor = FakeOperationMonitor()

    execution_engine = ExecutionEngine(trade_manager)
    profile_engine = ProfileEngine(
        accounts_provider=lambda profile_id: [account],
        execution_engine_instance=execution_engine,
    )
    signal_engine = SignalEngine(
        profiles_provider=lambda chat_id: [profile],
        profile_engine_instance=profile_engine,
        validator=lambda signal, profile: (True, []),
    )
    kraken_engine = KrakenEngine(
        signal_engine_instance=signal_engine,
        execution_engine_instance=execution_engine,
        operation_monitor_instance=operation_monitor,
    )

    client = FakeTelegramClient()
    register_telegram_listener(
        client,
        account_id=7,
        signal_processor=kraken_engine.process_telegram_signal,
    )
    kraken_engine.start()

    event = SimpleNamespace(
        chat_id=-100123,
        message=SimpleNamespace(
            id=99,
            message=(
                "SIGNAL - EmasVol20 (buy)\n"
                "Entry: 73505.99\n"
                "SL: 73486.47\n"
                "TP1: 73517.70\n"
                "TP2: 73529.41\n"
                "TP3: 73545.02"
            ),
        ),
    )

    asyncio.run(client.handler(event))
    kraken_engine.stop()

    assert trade_manager.reloaded is True
    assert operation_monitor.running is False
    assert len(trade_manager.received) == 1

    signal, received_profile, received_account = trade_manager.received[0]
    assert signal.source == "TELEGRAM"
    assert signal.telegram_account_id == 7
    assert signal.chat_id == -100123
    assert signal.message_id == 99
    assert signal.symbol == "EMASVOL20"
    assert signal.direction == "BUY"
    assert signal.entry == 73505.99
    assert signal.stop_loss == 73486.47
    assert signal.take_profits == [73517.70, 73529.41, 73545.02]
    assert signal.raw_message.startswith("SIGNAL")
    assert signal.received_at is not None
    assert received_profile is profile
    assert received_account is account
    assert "MetaTrader5" not in sys.modules
    assert "database.database_manager" not in sys.modules
