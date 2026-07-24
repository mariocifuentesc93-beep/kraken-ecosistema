"""Capa común de validación, persistencia y enrutamiento de señales."""

from dataclasses import dataclass
import logging
import traceback
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
    routed_profiles: tuple = ()


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
        event_log=None,
    ):
        self._use_default_event_log = repository is None and event_log is None
        self._repository = repository
        self._signal_engine = signal_engine_instance
        self._logger = logger or logging.getLogger(__name__)
        self._event_log = event_log

    def _get_repository(self):
        if self._repository is None:
            self._repository = SignalRepository()
        return self._repository

    def _get_signal_engine(self):
        if self._signal_engine is None:
            from engine.signal_engine import signal_engine
            self._signal_engine = signal_engine
        return self._signal_engine

    def _get_event_log(self):
        if self._event_log is None and self._use_default_event_log:
            from repositories.log_repository import log_repository
            self._event_log = log_repository
        return self._event_log

    def record_event(self, signal, stage, message, level="info"):
        identity = getattr(signal, "idempotency_key", None) or "sin-identidad"
        text = (
            f"{stage} | {identity} | "
            f"external_signal_id={getattr(signal, 'external_signal_id', None)} | "
            f"symbol={getattr(signal, 'symbol', '')} | {message}"
        )
        getattr(self._logger, level, self._logger.info)(text)
        event_log = self._get_event_log()
        if event_log is not None:
            getattr(event_log, level, event_log.info)(
                "InternalSignal",
                text,
            )

    def _set_status(self, signal, status):
        signal.status = status
        try:
            repository = self._get_repository()
            if hasattr(repository, "update_outcome"):
                repository.update_outcome(signal)
            else:
                repository.update_status(signal.id, status)
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
            self.record_event(
                signal,
                "IDENTITY_VALIDATION",
                reason,
                level="warning",
            )
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
        self.record_event(
            signal,
            "DETECTED",
            "Contrato INTERNAL validado; iniciando persistencia.",
        )
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
            self.record_event(
                persisted_signal,
                "DUPLICATE",
                reason,
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
            routed_profiles = []
            routed = bool(
                self._get_signal_engine().process(
                    signal=persisted_signal,
                    chat_id=persisted_signal.chat_id,
                    account_id=persisted_signal.telegram_account_id,
                    routed_profiles=routed_profiles,
                )
            )
        except Exception as error:
            reason = f"Falló el enrutamiento de la señal: {error}"
            persisted_signal.rejection_reason = reason
            persisted_signal.execution_decision = "FAILED"
            persisted_signal.metadata["failure_stage"] = "ROUTING_EXCEPTION"
            persisted_signal.metadata["rejection_reason"] = reason
            persisted_signal.metadata["execution_decision"] = "FAILED"
            persisted_signal.metadata["traceback"] = traceback.format_exc()
            self._set_status(persisted_signal, STATUS_FAILED)
            self._logger.exception(reason)
            self.record_event(
                persisted_signal,
                "ROUTING_EXCEPTION",
                f"{reason}\n{persisted_signal.metadata['traceback']}",
                level="error",
            )
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
            reason = (
                persisted_signal.rejection_reason
                or "SignalEngine no pudo enrutar la señal."
            )
            persisted_signal.rejection_reason = reason
            persisted_signal.execution_decision = (
                persisted_signal.execution_decision or "REJECTED"
            )
            persisted_signal.metadata.setdefault(
                "failure_stage", "ROUTING"
            )
            persisted_signal.metadata["rejection_reason"] = reason
            persisted_signal.metadata["execution_decision"] = (
                persisted_signal.execution_decision
            )
            self._set_status(persisted_signal, STATUS_FAILED)
            self._logger.warning(reason)
            self.record_event(
                persisted_signal,
                persisted_signal.metadata["failure_stage"],
                reason,
                level="warning",
            )
            return SignalIngestionResult(
                accepted=False,
                created=True,
                duplicate=False,
                signal=persisted_signal,
                reason=reason,
                routed=False,
            )

        persisted_signal.rejection_reason = ""
        persisted_signal.metadata.pop("failure_stage", None)
        persisted_signal.metadata["rejection_reason"] = ""
        status_error = self._set_status(persisted_signal, STATUS_ROUTED)
        reason = "Señal persistida y enrutada correctamente."
        self.record_event(
            persisted_signal,
            "ROUTED",
            (
                f"Perfiles={len(routed_profiles)} | "
                f"perfil={persisted_signal.profile_name or '-'} | "
                f"decisión={persisted_signal.execution_decision or '-'}"
            ),
        )
        return SignalIngestionResult(
            accepted=True,
            created=True,
            duplicate=False,
            signal=persisted_signal,
            reason=reason,
            routed=True,
            error=status_error,
            routed_profiles=tuple(routed_profiles),
        )


signal_ingestion_service = SignalIngestionService()
