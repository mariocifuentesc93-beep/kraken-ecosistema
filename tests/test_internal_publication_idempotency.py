import sqlite3

from repositories.telegram_publication_repository import (
    TelegramPublicationRepository,
)
from tests.test_internal_publication_service import service
from tests.test_telegram_signal_publisher import FakeClient
from tests.test_telegram_signal_formatter import make_signal


def test_same_signal_and_destination_is_not_resent(publication_repository):
    client = FakeClient()
    subject = service(publication_repository, client)
    first = subject.publish(make_signal())
    second = subject.publish(make_signal())
    assert first[0].sent is True
    assert second[0].already_sent is True
    assert len(client.calls) == 1


def test_two_distinct_signals_are_sent_to_same_destination(
    publication_repository,
):
    client = FakeClient()
    subject = service(publication_repository, client)
    first_signal = make_signal()
    second_signal = make_signal()
    second_signal.id = 11
    second_signal.external_signal_id = "12306"
    second_signal.idempotency_key = "INTERNAL:LIONX100:12306"
    publication_repository._connection.execute(
        """
        INSERT INTO signals(id, idempotency_key)
        VALUES (?, ?)
        """,
        (11, second_signal.idempotency_key),
    )
    publication_repository._connection.commit()

    assert subject.publish(first_signal)[0].sent is True
    assert subject.publish(second_signal)[0].sent is True
    assert len(client.calls) == 2


def test_unique_destination_is_shared_by_independent_connections(
    publication_repository,
):
    database_path = publication_repository._connection.execute(
        "PRAGMA database_list"
    ).fetchone()[2]
    second_connection = sqlite3.connect(database_path)
    second_connection.row_factory = sqlite3.Row
    second = TelegramPublicationRepository(second_connection)
    try:
        first_result = publication_repository.get_or_create(
            10,
            "INTERNAL:LIONX100:12305",
            7,
            -100123,
        )
        second_result = second.get_or_create(
            10,
            "INTERNAL:LIONX100:12305",
            7,
            -100123,
        )
        assert first_result.created is True
        assert second_result.created is False
        count = second_connection.execute(
            "SELECT COUNT(*) FROM telegram_publications"
        ).fetchone()[0]
        assert count == 1
    finally:
        second_connection.close()
