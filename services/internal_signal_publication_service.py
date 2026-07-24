"""Publicación opcional y desacoplada de señales INTERNAL."""

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
    def __init__(
        self,
        repository,
        publisher,
        profiles_provider,
        account_provider,
        logger=None,
    ):
        self._repository = repository
        self._publisher = publisher
        self._profiles_provider = profiles_provider
        self._account_provider = account_provider
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

    def _destinations(self, profiles):
        destinations = {}
        skipped = []
        for profile in profiles:
            if not getattr(profile, "publish_internal_to_telegram", False):
                continue
            account_id = self._integer(
                getattr(profile, "telegram_output_account_id", None),
                positive=True,
            )
            chat_id = self._integer(
                getattr(profile, "telegram_output_chat_id", None),
                positive=False,
            )
            account = (
                self._account_provider(account_id)
                if account_id is not None
                else None
            )
            if (
                account_id is None
                or chat_id is None
                or account is None
                or not getattr(account, "enabled", True)
            ):
                skipped.append(
                    InternalPublicationResult(
                        account_id,
                        chat_id,
                        "SKIPPED",
                        skipped=True,
                        error="Destino Telegram de salida inválido.",
                    )
                )
                continue
            destinations[(account_id, chat_id)] = (account_id, chat_id)
        return list(destinations.values()), skipped

    def publish(self, signal, profiles=None, retry_failed=False):
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
        profiles = (
            list(profiles)
            if profiles is not None
            else list(self._profiles_provider())
        )
        destinations, results = self._destinations(profiles)
        for account_id, chat_id in destinations:
            reservation = self._repository.get_or_create(
                signal.id,
                signal.idempotency_key,
                account_id,
                chat_id,
            )
            publication = reservation.publication
            if publication.status == SENT:
                results.append(
                    InternalPublicationResult(
                        account_id,
                        chat_id,
                        SENT,
                        already_sent=True,
                    )
                )
                continue
            if not reservation.created and (
                publication.status == PENDING
                or (publication.status == FAILED and not retry_failed)
            ):
                results.append(
                    InternalPublicationResult(
                        account_id,
                        chat_id,
                        publication.status,
                        skipped=True,
                        error=publication.last_error,
                    )
                )
                continue
            outcome = self._publisher.publish(
                signal,
                account_id,
                chat_id,
            )
            if outcome.success:
                self._repository.mark_sent(publication.id)
                results.append(
                    InternalPublicationResult(
                        account_id,
                        chat_id,
                        SENT,
                        sent=True,
                    )
                )
            else:
                self._repository.mark_failed(
                    publication.id,
                    outcome.error,
                )
                results.append(
                    InternalPublicationResult(
                        account_id,
                        chat_id,
                        FAILED,
                        error=outcome.error,
                    )
                )
        return results
