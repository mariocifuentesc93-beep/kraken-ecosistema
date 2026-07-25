from types import SimpleNamespace

from models.internal_publication_config import InternalPublicationConfig
from models.telegram_channel import TelegramChannel
from services.internal_signal_publication_service import (
    InternalSignalPublicationService,
)
from telegram.signal_publisher import TelegramSignalPublisher
from tests.test_telegram_signal_publisher import FakeClient
from tests.test_telegram_signal_formatter import make_signal


def enabled_account(account_id=7):
    return SimpleNamespace(id=account_id, enabled=True)


def config(enabled=True, account_id=7, chat_id=-100123):
    return InternalPublicationConfig(
        enabled=enabled,
        telegram_account_id=account_id,
        telegram_output_chat_id=chat_id,
    )


def service(
    repository,
    client,
    *,
    publication_config=None,
    account_exists=True,
    destinations=None,
):
    publication_config = publication_config or config()
    destinations = (
        [
            TelegramChannel(
                id=3,
                telegram_account_id=publication_config.telegram_account_id,
                chat_id=publication_config.telegram_output_chat_id,
                name="Señales",
                can_send=True,
                available=True,
            )
        ]
        if destinations is None
        else destinations
    )
    return InternalSignalPublicationService(
        repository=repository,
        publisher=TelegramSignalPublisher(lambda account_id: client),
        config_provider=lambda: publication_config,
        account_provider=lambda account_id: (
            enabled_account(account_id) if account_exists else None
        ),
        destinations_provider=lambda account_id: destinations,
    )


def test_global_publication_disabled_does_not_send(publication_repository):
    client = FakeClient()
    results = service(
        publication_repository,
        client,
        publication_config=config(enabled=False),
    ).publish(make_signal())
    assert results[0].skipped is True
    assert client.calls == []


def test_nonexistent_account_is_controlled(publication_repository):
    client = FakeClient()
    results = service(
        publication_repository,
        client,
        account_exists=False,
    ).publish(make_signal())
    assert results[0].skipped is True
    assert "cuenta" in results[0].error.lower()
    assert client.calls == []


def test_nonexistent_chat_is_controlled(publication_repository):
    client = FakeClient()
    results = service(
        publication_repository,
        client,
        destinations=[],
    ).publish(make_signal())
    assert results[0].skipped is True
    assert "chat" in results[0].error.lower()
    assert client.calls == []


def test_real_telegram_channel_model_is_used_by_attributes(
    publication_repository,
):
    client = FakeClient()
    results = service(publication_repository, client).publish(make_signal())
    assert results[0].sent is True
    assert results[0].telegram_channel_id == 3
    assert results[0].message_id == 1
    assert client.calls[0][0] == -100123


def test_unavailable_channel_is_rejected(publication_repository):
    client = FakeClient()
    channel = TelegramChannel(
        id=3,
        telegram_account_id=7,
        chat_id=-100123,
        can_send=True,
        available=False,
    )
    result = service(
        publication_repository,
        client,
        destinations=[channel],
    ).publish(make_signal())[0]
    assert result.skipped is True
    assert "disponible" in result.error.lower()
    assert client.calls == []


def test_channel_without_send_permission_is_rejected(
    publication_repository,
):
    client = FakeClient()
    channel = TelegramChannel(
        id=3,
        telegram_account_id=7,
        chat_id=-100123,
        can_send=False,
        available=True,
    )
    result = service(
        publication_repository,
        client,
        destinations=[channel],
    ).publish(make_signal())[0]
    assert result.skipped is True
    assert "permiso" in result.error.lower()
    assert client.calls == []


def test_global_destination_sends_once(publication_repository):
    client = FakeClient()
    publication_service = service(publication_repository, client)
    signal = make_signal()
    results = publication_service.publish(signal)
    repeated = publication_service.publish(signal)
    assert len(client.calls) == 1
    assert results[0].sent is True
    assert repeated[0].already_sent is True


def test_telegram_source_is_not_published(publication_repository):
    signal = make_signal()
    signal.source = "TELEGRAM"
    client = FakeClient()
    assert service(publication_repository, client).publish(signal) == []
    assert client.calls == []
