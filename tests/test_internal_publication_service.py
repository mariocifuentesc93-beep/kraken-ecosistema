from types import SimpleNamespace

from services.internal_signal_publication_service import (
    InternalSignalPublicationService,
)
from telegram.signal_publisher import TelegramSignalPublisher
from tests.test_telegram_signal_publisher import FakeClient
from tests.test_telegram_signal_formatter import make_signal


def enabled_account(account_id=7):
    return SimpleNamespace(id=account_id, enabled=True)


def profile(profile_id=1, enabled=True, account_id=7, chat_id=-100123):
    return SimpleNamespace(
        id=profile_id,
        publish_internal_to_telegram=enabled,
        telegram_output_account_id=account_id,
        telegram_output_chat_id=chat_id,
    )


def service(repository, profiles, client):
    return InternalSignalPublicationService(
        repository=repository,
        publisher=TelegramSignalPublisher(lambda account_id: client),
        profiles_provider=lambda: profiles,
        account_provider=lambda account_id: enabled_account(account_id),
    )


def test_disabled_profile_does_not_send(publication_repository):
    client = FakeClient()
    results = service(
        publication_repository,
        [profile(enabled=False)],
        client,
    ).publish(make_signal())
    assert results == []
    assert client.calls == []


def test_missing_output_destination_is_controlled(publication_repository):
    client = FakeClient()
    results = service(
        publication_repository,
        [profile(account_id=None, chat_id=None)],
        client,
    ).publish(make_signal())
    assert results[0].skipped is True
    assert client.calls == []


def test_two_profiles_same_destination_send_once(publication_repository):
    client = FakeClient()
    results = service(
        publication_repository,
        [profile(1), profile(2)],
        client,
    ).publish(make_signal())
    assert len(client.calls) == 1
    assert sum(item.sent for item in results) == 1


def test_telegram_source_is_not_published(publication_repository):
    signal = make_signal()
    signal.source = "TELEGRAM"
    client = FakeClient()
    results = service(
        publication_repository,
        [profile()],
        client,
    ).publish(signal)
    assert results == []
    assert client.calls == []
