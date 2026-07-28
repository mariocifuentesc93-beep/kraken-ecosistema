"""Global, optional and idempotent publication of INTERNAL signals."""

from dataclasses import dataclass
import hashlib
import json
import logging

from repositories.telegram_publication_repository import (
    FAILED,
    PENDING,
    SENT,
)


@dataclass(frozen=True)
class InternalPublicationResult:
    telegram_account_id: int | None
    chat_id: int | None
    status: str
    telegram_channel_id: int | None = None
    sent: bool = False
    already_sent: bool = False
    skipped: bool = False
    error: str | None = None
    message_id: int | None = None
    traceback: str | None = None


class InternalSignalPublicationService:
    """Publish each persisted INTERNAL signal to one global destination."""

    def __init__(
        self,
        repository,
        publisher,
        config_provider,
        account_provider,
        destinations_provider,
        logger=None,
    ):
        self._repository = repository
        self._publisher = publisher
        self._config_provider = config_provider
        self._account_provider = account_provider
        self._destinations_provider = destinations_provider
        self._logger = logger or logging.getLogger(__name__)

    @staticmethod
    def _integer(value, *, positive):
        if isinstance(value, bool) or value is None:
            return None
        try:
            result = int(str(value).strip())
        except (TypeError, ValueError):
            return None
        if positive and result <= 0:
            return None
        if not positive and result == 0:
            return None
        return result

    def _destination(self):
        config = self._config_provider()
        if config is None or not getattr(config, "enabled", False):
            return None, InternalPublicationResult(
                None,
                None,
                "SKIPPED",
                skipped=True,
                error="La publicación global de INTERNAL está desactivada.",
            )
        account_id = self._integer(
            getattr(config, "telegram_account_id", None),
            positive=True,
        )
        chat_id = self._integer(
            getattr(config, "telegram_output_chat_id", None),
            positive=False,
        )
        account = (
            self._account_provider(account_id)
            if account_id is not None
            else None
        )
        if (
            account_id is None
            or account is None
            or not getattr(account, "enabled", True)
        ):
            return None, InternalPublicationResult(
                account_id,
                chat_id,
                "SKIPPED",
                skipped=True,
                error="La cuenta Telegram global no existe o está deshabilitada.",
            )
        destinations = self._destinations_provider(account_id)
        channel = next(
            (
                item
                for item in destinations
                if self._integer(
                    getattr(item, "chat_id", None),
                    positive=False,
                ) == chat_id
                and self._integer(
                    getattr(item, "telegram_account_id", None),
                    positive=True,
                ) == account_id
            ),
            None,
        )
        if chat_id is None or channel is None:
            return None, InternalPublicationResult(
                account_id,
                chat_id,
                "SKIPPED",
                skipped=True,
                error="El chat o canal global no existe para esta cuenta.",
            )
        channel_id = self._integer(
            getattr(channel, "id", None),
            positive=True,
        )
        if not bool(getattr(channel, "is_available", False)):
            return None, InternalPublicationResult(
                account_id,
                chat_id,
                "SKIPPED",
                telegram_channel_id=channel_id,
                skipped=True,
                error="El chat o canal global no está disponible.",
            )
        if not bool(getattr(channel, "can_send", False)):
            return None, InternalPublicationResult(
                account_id,
                chat_id,
                "SKIPPED",
                telegram_channel_id=channel_id,
                skipped=True,
                error="La cuenta no tiene permiso para enviar al destino.",
            )
        return (account_id, chat_id, channel_id), None

    def destination_details(self):
        """Resuelve el destino sin reservar ni enviar."""
        destination, skipped = self._destination()
        if skipped is not None:
            return {
                "telegram_account_id": skipped.telegram_account_id,
                "telegram_channel_id": skipped.telegram_channel_id,
                "chat_id": skipped.chat_id,
                "error": skipped.error,
            }
        account_id, chat_id, channel_id = destination
        return {
            "telegram_account_id": account_id,
            "telegram_channel_id": channel_id,
            "chat_id": chat_id,
            "error": None,
        }

    def publish(self, signal, retry_failed=False):
        if str(getattr(signal, "source", "")).strip().upper() != "INTERNAL":
            return []
        if getattr(signal, "id", None) is None:
            return [
                InternalPublicationResult(
                    None,
                    None,
                    "SKIPPED",
                    skipped=True,
                    error="La señal debe estar persistida antes de publicar.",
                )
            ]

        destination, skipped = self._destination()
        if skipped is not None:
            return [skipped]
        account_id, chat_id, channel_id = destination
        reservation = self._repository.get_or_create(
            signal.id,
            signal.idempotency_key,
            account_id,
            chat_id,
        )
        publication = reservation.publication
        if publication.status == SENT:
            return [
                InternalPublicationResult(
                    account_id,
                    chat_id,
                    SENT,
                    telegram_channel_id=channel_id,
                    already_sent=True,
                )
            ]
        if not reservation.created and (
            publication.status == PENDING
            or (publication.status == FAILED and not retry_failed)
        ):
            return [
                InternalPublicationResult(
                    account_id,
                    chat_id,
                    publication.status,
                    telegram_channel_id=channel_id,
                    skipped=True,
                    error=publication.last_error,
                )
            ]

        outcome = self._publisher.publish(signal, account_id, chat_id)
        if outcome.success:
            self._repository.mark_sent(publication.id)
            return [
                InternalPublicationResult(
                    account_id,
                    chat_id,
                    SENT,
                    telegram_channel_id=channel_id,
                    sent=True,
                    message_id=outcome.message_id,
                )
            ]

        self._repository.mark_failed(publication.id, outcome.error)
        return [
            InternalPublicationResult(
                account_id,
                chat_id,
                FAILED,
                telegram_channel_id=channel_id,
                error=outcome.error,
                traceback=outcome.traceback,
            )
        ]

    def publish_update(self, signal, update):
        """Publica una sola notificación consolidada por cambio detectado."""
        from telegram.signal_publisher import format_internal_level_update

        destination, skipped = self._destination()
        if skipped is not None:
            return [skipped]
        account_id, chat_id, channel_id = destination
        fingerprint = hashlib.sha256(
            json.dumps(
                update.changes, sort_keys=True, default=str
            ).encode("utf-8")
        ).hexdigest()[:24]
        update_key = f"{update.signal_key}:LEVELS:{fingerprint}"
        reservation = self._repository.get_or_create(
            signal.id,
            update_key,
            account_id,
            chat_id,
        )
        publication = reservation.publication
        if publication.status == SENT:
            return [
                InternalPublicationResult(
                    account_id,
                    chat_id,
                    SENT,
                    telegram_channel_id=channel_id,
                    already_sent=True,
                )
            ]
        if not reservation.created and publication.status == PENDING:
            return [
                InternalPublicationResult(
                    account_id,
                    chat_id,
                    PENDING,
                    telegram_channel_id=channel_id,
                    skipped=True,
                )
            ]
        outcome = self._publisher.publish_text(
            format_internal_level_update(signal, update),
            account_id,
            chat_id,
            reference=update_key,
        )
        if outcome.success:
            self._repository.mark_sent(publication.id)
        else:
            self._repository.mark_failed(publication.id, outcome.error)
        return [
            InternalPublicationResult(
                account_id,
                chat_id,
                SENT if outcome.success else FAILED,
                telegram_channel_id=channel_id,
                sent=outcome.success,
                error=outcome.error,
                message_id=outcome.message_id,
                traceback=outcome.traceback,
            )
        ]
