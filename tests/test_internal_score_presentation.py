from dashboard.pages.signal_inspector_page import SignalInspectorPage
from models.signal import Signal


def test_internal_zero_score_is_presented_as_not_applicable():
    signal = Signal(
        source="INTERNAL",
        external_signal_id="13000",
        symbol="LionX150",
        direction="BUY",
        entry=100.0,
        stop_loss=90.0,
        take_profits=[110.0, 120.0, 130.0],
        score=0.0,
    )

    assert SignalInspectorPage.score_text(signal) == "N/A"


def test_telegram_score_keeps_numeric_presentation():
    signal = Signal(
        source="TELEGRAM",
        telegram_account_id=1,
        chat_id=-100123,
        message_id=10,
        symbol="LionX150",
        direction="BUY",
        entry=100.0,
        stop_loss=90.0,
        take_profits=[110.0],
        score=96.0,
    )

    assert SignalInspectorPage.score_text(signal) == "96"
