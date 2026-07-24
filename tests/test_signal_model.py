from datetime import datetime

from models.signal import Signal


def test_signal_model_supports_telegram_contract():
    received_at = datetime(2026, 7, 23, 10, 30)
    signal = Signal(
        source="telegram",
        telegram_account_id=7,
        chat_id=-100123,
        message_id=99,
        received_at=received_at,
        symbol="EmasVol20",
        direction="buy",
        entry=73505.99,
        stop_loss=73486.47,
        take_profits=[73517.70, 73529.41, 73545.02],
        metadata={"provider": "test"},
    )

    assert signal.source == "TELEGRAM"
    assert signal.direction == "BUY"
    assert signal.idempotency_key == "TELEGRAM:7:-100123:99"
    assert signal.received_at == received_at
    assert signal.tp1 == 73517.70
    assert signal.tp2 == 73529.41
    assert signal.tp3 == 73545.02


def test_signal_model_can_represent_future_internal_signal():
    signal = Signal(
        source="internal",
        external_signal_id=12241,
        detected_at="2026-07-23T11:00:00",
        symbol="LionX75",
        direction="sell",
        entry=202870.0,
        stop_loss=203000.0,
        take_profits=[202787.66, 202700.0, 202600.0],
    )

    assert signal.source == "INTERNAL"
    assert signal.external_signal_id == "12241"
    assert signal.idempotency_key == "INTERNAL:12241"
    assert signal.detected_at == datetime(2026, 7, 23, 11, 0)
