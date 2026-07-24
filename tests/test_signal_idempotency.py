import sqlite3

import pytest

from database.signal_contract_migration import upgrade
from models.signal import Signal, SignalIdentityError
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


@pytest.mark.parametrize(
    "account_id",
    ["", "   ", "not-a-number", True, False],
)
def test_telegram_rejects_invalid_account_id(
    unified_database,
    account_id,
):
    repository = SignalRepository(unified_database)
    signal = Signal(
        source="TELEGRAM",
        telegram_account_id=account_id,
        chat_id=-100123,
        message_id=99,
    )

    with pytest.raises(SignalIdentityError):
        repository.create(signal)

    assert repository.count() == 0


@pytest.mark.parametrize(
    "identity",
    [
        {
            "telegram_account_id": None,
            "chat_id": -100123,
            "message_id": 99,
        },
        {
            "telegram_account_id": 7,
            "chat_id": None,
            "message_id": 99,
        },
        {
            "telegram_account_id": 7,
            "chat_id": -100123,
            "message_id": None,
        },
        {
            "telegram_account_id": 7,
            "chat_id": " ",
            "message_id": 99,
        },
        {
            "telegram_account_id": 7,
            "chat_id": -100123,
            "message_id": True,
        },
    ],
)
def test_telegram_requires_every_valid_identity_field(
    unified_database,
    identity,
):
    repository = SignalRepository(unified_database)

    with pytest.raises(SignalIdentityError):
        repository.create(Signal(source="TELEGRAM", **identity))

    assert repository.count() == 0


def test_telegram_accepts_negative_chat_and_zero_ids(unified_database):
    repository = SignalRepository(unified_database)
    result = repository.create(
        Signal(
            source="TELEGRAM",
            telegram_account_id="0",
            chat_id="-100123",
            message_id="0",
        )
    )

    assert result.signal.telegram_account_id == 0
    assert result.signal.chat_id == -100123
    assert result.signal.message_id == 0
    assert result.signal.idempotency_key == "TELEGRAM:0:-100123:0"


def test_telegram_accepts_matching_manual_key(unified_database):
    result = SignalRepository(unified_database).create(
        Signal(
            source="TELEGRAM",
            telegram_account_id=7,
            chat_id=-100123,
            message_id=99,
            idempotency_key=" TELEGRAM:7:-100123:99 ",
        )
    )

    assert result.signal.idempotency_key == "TELEGRAM:7:-100123:99"


def test_telegram_rejects_mismatching_manual_key(unified_database):
    repository = SignalRepository(unified_database)

    with pytest.raises(SignalIdentityError):
        repository.create(
            Signal(
                source="TELEGRAM",
                telegram_account_id=7,
                chat_id=-100123,
                message_id=99,
                idempotency_key="TELEGRAM:7:-100123:100",
            )
        )


@pytest.mark.parametrize(
    "external_signal_id",
    [None, "", "   ", True, False],
)
def test_internal_requires_external_signal_id(
    unified_database,
    external_signal_id,
):
    repository = SignalRepository(unified_database)

    with pytest.raises(SignalIdentityError):
        repository.create(
            Signal(
                source="INTERNAL",
                external_signal_id=external_signal_id,
            )
        )


def test_internal_accepts_matching_manual_key(unified_database):
    result = SignalRepository(unified_database).create(
        Signal(
            source="INTERNAL",
            external_signal_id=" 12241 ",
            idempotency_key=" INTERNAL:12241 ",
        )
    )

    assert result.signal.external_signal_id == "12241"
    assert result.signal.idempotency_key == "INTERNAL:12241"


def test_internal_rejects_mismatching_manual_key(unified_database):
    with pytest.raises(SignalIdentityError):
        SignalRepository(unified_database).create(
            Signal(
                source="INTERNAL",
                external_signal_id="12241",
                idempotency_key="INTERNAL:99999",
            )
        )


@pytest.mark.parametrize("idempotency_key", ["", "   "])
def test_empty_manual_key_is_rejected(
    unified_database,
    idempotency_key,
):
    repository = SignalRepository(unified_database)

    with pytest.raises(SignalIdentityError):
        repository.create(
            Signal(
                source="TELEGRAM",
                telegram_account_id=7,
                chat_id=-100123,
                message_id=99,
                idempotency_key=idempotency_key,
            )
        )

    assert repository.count() == 0


def test_distinct_signals_cannot_collide_on_blank_key(unified_database):
    repository = SignalRepository(unified_database)

    for signal in (
        Signal(
            source="TELEGRAM",
            telegram_account_id=7,
            chat_id=-100123,
            message_id=99,
            idempotency_key=" ",
        ),
        Signal(
            source="INTERNAL",
            external_signal_id="12241",
            idempotency_key=" ",
        ),
    ):
        with pytest.raises(SignalIdentityError):
            repository.create(signal)

    assert repository.count() == 0


@pytest.mark.parametrize("source", ["UNKNOWN", "LEGACY"])
def test_normal_create_rejects_unsupported_or_legacy_source(
    unified_database,
    source,
):
    with pytest.raises(SignalIdentityError):
        SignalRepository(unified_database).create(
            Signal(
                source=source,
                external_signal_id="1",
                idempotency_key=f"{source}:1",
            )
        )


def test_duplicate_with_two_independent_connections(tmp_path):
    database_path = tmp_path / "concurrent.db"
    first_connection = sqlite3.connect(database_path, timeout=5)
    first_connection.row_factory = sqlite3.Row
    upgrade(first_connection)
    second_connection = sqlite3.connect(database_path, timeout=5)
    second_connection.row_factory = sqlite3.Row

    try:
        first_repository = SignalRepository(first_connection)
        second_repository = SignalRepository(second_connection)
        identity = {
            "source": "TELEGRAM",
            "telegram_account_id": 7,
            "chat_id": -100123,
            "message_id": 99,
        }

        first = first_repository.create(
            Signal(**identity, symbol="FIRST")
        )
        second = second_repository.create(
            Signal(**identity, symbol="SECOND")
        )

        assert first.created is True
        assert second.already_existed is True
        assert second.signal.id == first.signal.id
        assert second.signal.symbol == "FIRST"
        assert first_repository.count() == 1
    finally:
        first_connection.close()
        second_connection.close()
