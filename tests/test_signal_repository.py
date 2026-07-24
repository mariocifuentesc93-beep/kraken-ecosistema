from datetime import datetime

from models.signal import Signal
from repositories.signal_repository import SignalRepository


def test_signal_round_trip_preserves_json_and_dates(unified_database):
    repository = SignalRepository(unified_database)
    signal = Signal(
        source="TELEGRAM",
        telegram_account_id=3,
        chat_id=-100777,
        message_id=42,
        received_at=datetime(2026, 7, 23, 12, 1, 2),
        detected_at=datetime(2026, 7, 23, 12, 1, 1),
        symbol="EmasVol90",
        direction="BUY",
        entry=100.5,
        stop_loss=99.5,
        take_profits=[101.0, 102.0, 103.0],
        raw_message="SIGNAL EmasVol90 buy",
        metadata={"rating": "Medium", "nested": {"valid": True}},
        status="RECEIVED",
        score=96,
    )

    result = repository.create(signal)
    restored = repository.get_by_id(result.signal.id)

    assert result.created is True
    assert restored == signal
    assert restored.take_profits == [101.0, 102.0, 103.0]
    assert restored.metadata == {
        "nested": {"valid": True},
        "rating": "Medium",
    }
    assert repository.get_by_idempotency_key(
        "TELEGRAM:3:-100777:42"
    ) == restored
    assert repository.exists_by_idempotency_key(restored.idempotency_key)
    assert repository.list() == [restored]
