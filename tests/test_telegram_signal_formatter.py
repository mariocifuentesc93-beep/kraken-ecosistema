from models.signal import Signal
from telegram.signal_publisher import format_internal_telegram_signal


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
        "TP3: 253437.7\n\n"
        "Signal ID: 12305"
    )
    assert "INTERNAL:LIONX100:12305" not in message


def test_sell_format_is_exact():
    message = format_internal_telegram_signal(make_signal("sell"))
    assert message.startswith("SIGNAL - LionX100 (SELL)\n\n")
    assert message.endswith("Signal ID: 12305")


def test_prices_keep_at_most_four_decimals_without_trailing_zeroes():
    signal = make_signal()
    signal.entry = 73505.9900
    signal.stop_loss = 239659.4703
    signal.take_profits = [73517.7000, 1.23456, 10.0000]
    message = format_internal_telegram_signal(signal)
    assert "Entry: 73505.99" in message
    assert "SL: 239659.4703" in message
    assert "TP1: 73517.7" in message
    assert "TP2: 1.2346" in message
    assert "TP3: 10" in message
