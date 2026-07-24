from models.signal import Signal
from repositories.signal_repository import SignalRepository


def test_duplicate_telegram_signal_returns_existing_row(unified_database):
    repository = SignalRepository(unified_database)

    first = repository.create(
        Signal(
            source="TELEGRAM",
            telegram_account_id=7,
            chat_id=-100123,
            message_id=99,
            symbol="EmasVol20",
        )
    )
    second = repository.create(
        Signal(
            source="TELEGRAM",
            telegram_account_id=7,
            chat_id=-100123,
            message_id=99,
            symbol="ChangedValue",
        )
    )

    assert first.created is True
    assert second.created is False
    assert second.already_existed is True
    assert second.signal.id == first.signal.id
    assert second.signal.symbol == "EmasVol20"
    assert repository.count() == 1


def test_duplicate_internal_signal_returns_existing_row(unified_database):
    repository = SignalRepository(unified_database)

    first = repository.create(
        Signal(
            source="INTERNAL",
            external_signal_id="12241",
            symbol="LionX75",
        )
    )
    second = repository.create(
        Signal(
            source="INTERNAL",
            external_signal_id=12241,
            symbol="Other",
        )
    )

    assert first.created is True
    assert second.already_existed is True
    assert second.signal.id == first.signal.id
    assert repository.count() == 1
