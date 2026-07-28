from types import SimpleNamespace

from mt5.executor import MT5Executor


def test_executor_uses_profile_selected_take_profit():
    signal = SimpleNamespace(take_profits=[101.0, 102.0, 103.0])

    assert MT5Executor._target_take_profit(
        signal, SimpleNamespace(tp_level=2)
    ) == 102.0


def test_executor_clamps_take_profit_level_to_available_targets():
    signal = SimpleNamespace(take_profits=[101.0, 102.0, 103.0])

    assert MT5Executor._target_take_profit(
        signal, SimpleNamespace(tp_level=10)
    ) == 103.0
    assert MT5Executor._target_take_profit(signal, None) == 101.0
