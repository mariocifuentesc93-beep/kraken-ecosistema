from tests.test_internal_publication_service import profile, service
from tests.test_telegram_signal_publisher import FakeClient
from tests.test_telegram_signal_formatter import make_signal
import sqlite3

from repositories.telegram_publication_repository import (
    TelegramPublicationRepository,
)


def test_same_signal_and_destination_is_not_resent(publication_repository):
    client = FakeClient()
    subject = service(publication_repository, [profile()], client)
    first = subject.publish(make_signal())
    second = subject.publish(make_signal())
    assert first[0].sent is True
    assert second[0].already_sent is True
    assert len(client.calls) == 1


def test_same_signal_is_sent_once_to_each_destination(
    publication_repository,
):
    client = FakeClient()
    subject = service(
        publication_repository,
        [profile(1, chat_id=-1001), profile(2, chat_id=-1002)],
        client,
    )
    results = subject.publish(make_signal())
    assert len(client.calls) == 2
    assert sum(item.sent for item in results) == 2


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
