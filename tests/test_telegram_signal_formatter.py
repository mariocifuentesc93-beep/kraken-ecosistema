from datetime import datetime

from internal.signal_level_update import InternalSignalLevelUpdate
from models.signal import Signal
import pytest

from telegram.signal_publisher import (
    format_internal_level_update,
    format_internal_telegram_signal,
    format_signal_price,
)


def make_signal(direction="BUY"):
    return Signal(
        id=10,
        source="INTERNAL",
        external_signal_id="12305",
        symbol="LionX100",
        direction=direction,
        entry=253740.1800,
        stop_loss=253891.4200,
        take_profits=[253649.4400, 253558.6900, 253437.7000],
    )


def test_buy_format_is_exact_and_does_not_expose_internal_key():
    message = format_internal_telegram_signal(make_signal())
    assert message == (
        "SIGNAL - LionX100 (BUY)\n\n"
        "Entry: 253740.18\n"
        "SL: 253891.42\n"
        "TP1: 253649.44\n"
        "TP2: 253558.69\n"
        "TP3: 253437.70\n\n"
        "Signal ID: 12305"
    )
    assert "INTERNAL:LIONX100:12305" not in message


def test_sell_format_is_exact():
    message = format_internal_telegram_signal(make_signal("sell"))
    assert message == (
        "SIGNAL - LionX100 (SELL)\n\n"
        "Entry: 253740.18\n"
        "SL: 253891.42\n"
        "TP1: 253649.44\n"
        "TP2: 253558.69\n"
        "TP3: 253437.70\n\n"
        "Signal ID: 12305"
    )
    assert "INTERNAL:LIONX100:12305" not in message
    assert not any(marker in message for marker in ("*", "#", "<", ">"))
    assert "🚨" not in message


def test_level_update_format_is_plain_and_only_lists_changes():
    signal = make_signal("sell")
    update = InternalSignalLevelUpdate(
        symbol="LIONX100",
        external_signal_id="12305",
        direction="SELL",
        previous_stop_loss=253891.42,
        stop_loss=253850.0,
        previous_take_profits=(253649.44, 253558.69, 253437.70),
        take_profits=(253640.0, 253558.69, 253437.70),
        detected_at=datetime(2026, 7, 28, 12, 0),
    )

    assert format_internal_level_update(signal, update) == (
        "SIGNAL UPDATE - LionX100 (SELL)\n\n"
        "SL: 253891.42 -> 253850.00\n"
        "TP1: 253649.44 -> 253640.00\n\n"
        "Signal ID: 12305"
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (73505.9900, "73505.99"),
        (73517.7000, "73517.70"),
        (253437.7000, "253437.70"),
        (239659.4703, "239659.4703"),
        (100.0000, "100.00"),
        (100.1000, "100.10"),
        (100.1230, "100.123"),
        (100.1234, "100.1234"),
    ],
)
def test_prices_keep_between_two_and_four_decimals(value, expected):
    assert format_signal_price(value) == expected
