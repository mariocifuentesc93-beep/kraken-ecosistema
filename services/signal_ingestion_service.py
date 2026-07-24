"""Capa común de validación, persistencia y enrutamiento de señales."""

from dataclasses import dataclass
import logging
from typing import Optional

from models.signal import Signal, SignalIdentityError
from repositories.signal_repository import SignalRepository


STATUS_RECEIVED = "RECEIVED"
STATUS_ROUTED = "ROUTED"
STATUS_FAILED = "FAILED"


@dataclass(frozen=True)
class SignalIngestionResult:
    accepted: bool
    created: bool
    duplicate: bool
    signal: Optional[Signal]
    reason: str
    routed: bool
    error: Optional[str] = None


class SignalIngestionService:
    """
    Persiste una señal una sola vez antes de entregarla a SignalEngine.

    El repositorio, el motor y el logger son inyectables para que las pruebas
    no necesiten la base real, Telethon ni MetaTrader5.
    """

    def __init__(
        self,
        repository=None,
        signal_engine_instance=None,
        logger=None,
    ):
        self._repository = repository
        self._signal_engine = signal_engine_instance
        self._logger = logger or logging.getLogger(__name__)

    def _get_repository(self):
        if self._repository is None:
            self._repository = SignalRepository()
        return self._repository

    def _get_signal_engine(self):
        if self._signal_engine is None:
            from engine.signal_engine import signal_engine
            self._signal_engine = signal_engine
        return self._signal_engine

    def _set_status(self, signal, status):
        signal.status = status
        try:
            self._get_repository().update_status(signal.id, status)
            return None
        except Exception as error:
            self._logger.error(
                "No se pudo actualizar el estado de la señal %s a %s: %s",
                signal.id,
                status,
                error,
            )
            return str(error)

    def ingest(
        self,
        signal,
        chat_id=None,
        account_id=None,
    ):
        if not isinstance(signal, Signal):
            reason = "La entrada debe ser una instancia de Signal."
            self._logger.warning(reason)
            return SignalIngestionResult(
                accepted=False,
                created=False,
                duplicate=False,
                signal=None,
                reason=reason,
                routed=False,
                error=reason,
            )

        if chat_id is not None:
            signal.chat_id = chat_id
        if account_id is not None:
            signal.telegram_account_id = account_id

        try:
            signal.validate_persistent_identity()
        except SignalIdentityError as error:
            reason = f"Identidad de señal inválida: {error}"
            self._logger.warning(reason)
            return SignalIngestionResult(
                accepted=False,
                created=False,
                duplicate=False,
                signal=signal,
                reason=reason,
                routed=False,
                error=str(error),
            )

        signal.status = STATUS_RECEIVED
        try:
            persistence = self._get_repository().create(signal)
        except Exception as error:
            reason = f"No se pudo persistir la señal: {error}"
            self._logger.exception(reason)
            return SignalIngestionResult(
                accepted=False,
                created=False,
                duplicate=False,
                signal=signal,
                reason=reason,
                routed=False,
                error=str(error),
            )

        persisted_signal = persistence.signal
        if not persistence.created:
            reason = (
                "Señal duplicada; se conserva la fila existente y "
                "no se vuelve a enrutar."
            )
            self._logger.info(
                "%s Clave: %s",
                reason,
                persisted_signal.idempotency_key,
            )
            return SignalIngestionResult(
                accepted=False,
                created=False,
                duplicate=True,
                signal=persisted_signal,
                reason=reason,
                routed=False,
            )

        try:
            routed = bool(
                self._get_signal_engine().process(
                    signal=persisted_signal,
                    chat_id=persisted_signal.chat_id,
                    account_id=persisted_signal.telegram_account_id,
                )
            )
        except Exception as error:
            self._set_status(persisted_signal, STATUS_FAILED)
            reason = f"Falló el enrutamiento de la señal: {error}"
            self._logger.exception(reason)
            return SignalIngestionResult(
                accepted=False,
                created=True,
                duplicate=False,
                signal=persisted_signal,
                reason=reason,
                routed=False,
                error=str(error),
            )

        if not routed:
            self._set_status(persisted_signal, STATUS_FAILED)
            reason = "SignalEngine no pudo enrutar la señal."
            self._logger.warning(reason)
            return SignalIngestionResult(
                accepted=False,
                created=True,
                duplicate=False,
                signal=persisted_signal,
                reason=reason,
                routed=False,
            )

        status_error = self._set_status(persisted_signal, STATUS_ROUTED)
        reason = "Señal persistida y enrutada correctamente."
        return SignalIngestionResult(
            accepted=True,
            created=True,
            duplicate=False,
            signal=persisted_signal,
            reason=reason,
            routed=True,
            error=status_error,
        )


signal_ingestion_service = SignalIngestionService()
