"""Global, optional and idempotent publication of INTERNAL signals."""

from dataclasses import dataclass
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
    sent: bool = False
    already_sent: bool = False
    skipped: bool = False
    error: str | None = None


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
        if chat_id is None or not any(
            self._integer(item.get("chat_id"), positive=False) == chat_id
            for item in destinations
        ):
            return None, InternalPublicationResult(
                account_id,
                chat_id,
                "SKIPPED",
                skipped=True,
                error="El chat o canal global no existe para esta cuenta.",
            )
        return (account_id, chat_id), None

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
        account_id, chat_id = destination
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
                    sent=True,
                )
            ]

        self._repository.mark_failed(publication.id, outcome.error)
        return [
            InternalPublicationResult(
                account_id,
                chat_id,
                FAILED,
                error=outcome.error,
            )
        ]
