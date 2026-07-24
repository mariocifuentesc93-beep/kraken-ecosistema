from engine.execution_engine import ExecutionEngine
from engine.profile_engine import ProfileEngine
from engine.signal_engine import SignalEngine


class MutatingTradeManager:
    def __init__(self):
        self.signals = []

    def process_signal(self, signal, profile, account):
        self.signals.append(signal)
        signal.metadata["processed_by"] = account.id
        signal.take_profits.append(float(account.id))
        return True


def test_each_profile_and_account_receives_an_independent_signal(
    valid_signal,
    profile_factory,
    account_factory,
):
    profiles = [
        profile_factory(1, "Profile one"),
        profile_factory(2, "Profile two"),
    ]
    accounts = {
        1: [account_factory(11), account_factory(12)],
        2: [account_factory(21)],
    }
    trade_manager = MutatingTradeManager()
    execution_engine = ExecutionEngine(trade_manager)
    execution_engine.running = True
    profile_engine = ProfileEngine(
        accounts_provider=lambda profile_id: accounts[profile_id],
        execution_engine_instance=execution_engine,
    )
    signal_engine = SignalEngine(
        profiles_provider=lambda chat_id: profiles,
        profile_engine_instance=profile_engine,
        validator=lambda signal, profile: (True, []),
    )
    signal_engine.start()

    original_take_profits = list(valid_signal.take_profits)
    original_metadata = dict(valid_signal.metadata)

    assert signal_engine.process(
        valid_signal,
        chat_id=valid_signal.chat_id,
        account_id=valid_signal.telegram_account_id,
    )

    received = trade_manager.signals
    assert len(received) == 3
    assert len({id(signal) for signal in received}) == 3
    assert [signal.profile_id for signal in received] == [1, 1, 2]
    assert [signal.mt5_account_id for signal in received] == [11, 12, 21]
    assert [signal.metadata["processed_by"] for signal in received] == [
        11,
        12,
        21,
    ]
    assert valid_signal.take_profits == original_take_profits
    assert valid_signal.metadata == original_metadata
