from copy import deepcopy

from core.event_bus import event_bus
from core.events import (
    SignalReceivedEvent,
    SignalRejectedEvent,
    SignalProcessedEvent,
)


class SignalEngine:

    def __init__(
        self,
        profiles_provider=None,
        internal_profiles_provider=None,
        profile_engine_instance=None,
        validator=None,
        source_router=None,
    ):
        self.running = False
        self._profiles_provider = profiles_provider
        self._internal_profiles_provider = internal_profiles_provider
        self._profile_engine = profile_engine_instance
        self._validator = validator
        self._source_router = source_router

    def _get_profiles(self, signal, chat_id):
        if signal.source == "INTERNAL":
            if self._internal_profiles_provider is None:
                from repositories.profile_repository import (
                    profile_repository,
                )
                self._internal_profiles_provider = (
                    profile_repository.get_internal_profiles
                )
            return self._internal_profiles_provider()

        if signal.source != "TELEGRAM":
            return []

        if self._profiles_provider is None:
            from repositories.profile_repository import profile_repository
            self._profiles_provider = (
                profile_repository.get_profiles_by_chat
            )

        return self._profiles_provider(chat_id)

    def _get_source_router(self):
        if self._source_router is None:
            from engine.profile_source_router import profile_source_router
            self._source_router = profile_source_router
        return self._source_router

    def _get_profile_engine(self):
        if self._profile_engine is None:
            from engine.profile_engine import profile_engine
            self._profile_engine = profile_engine

        return self._profile_engine

    def _validate(self, signal, profile):
        if self._validator is None:
            from core.signal_validator import validate_signal
            self._validator = validate_signal

        return self._validator(signal, profile=profile)

    def start(self):
        self.running = True
        event_bus.log("SignalEngine iniciado.")

    def stop(self):
        self.running = False
        event_bus.log("SignalEngine detenido.")

    def process(
        self,
        signal,
        chat_id,
        account_id=None,
    ):
        """
        Procesa una señal normalizada y ya persistida.

        Este método es el único responsable de resolver los perfiles asociados
        al chat. Cada perfil recibe una copia independiente del Signal.
        """

        if not self.running:
            event_bus.warning("SignalEngine detenido.")
            return False

        if chat_id is not None:
            signal.chat_id = chat_id
        if account_id is not None:
            signal.telegram_account_id = account_id

        event_bus.signalReceived.emit(
            SignalReceivedEvent(
                signal=signal,
                chat_id=chat_id,
                telegram_account_id=account_id,
            )
        )

        profiles = self._get_profiles(signal, chat_id)
        profiles = self._get_source_router().filter(profiles, signal)

        if not profiles:
            reason = (
                f"No existen perfiles habilitados para {signal.source}"
            )
            if signal.source == "TELEGRAM":
                reason += f" en el chat {chat_id}"
            event_bus.signalRejected.emit(
                SignalRejectedEvent(signal=signal, reason=reason)
            )
            event_bus.warning(reason)
            return False

        executed = False

        for profile in profiles:
            if not getattr(profile, "enabled", True):
                continue

            profile_signal = deepcopy(signal)
            profile_signal.profile_id = profile.id
            profile_signal.profile_name = profile.name

            valid, errors = self._validate(profile_signal, profile)

            if not valid:
                reason = "; ".join(errors)
                event_bus.signalRejected.emit(
                    SignalRejectedEvent(
                        signal=profile_signal,
                        reason=reason,
                    )
                )
                event_bus.warning(
                    f"Perfil '{profile.name}' rechazó la señal: {reason}"
                )
                continue

            result = self._get_profile_engine().process_signal(
                signal=profile_signal,
                profile=profile,
            )

            if result:
                executed = True

        if executed:
            event_bus.signalProcessed.emit(
                SignalProcessedEvent(signal=signal)
            )
            event_bus.log("La señal fue enviada correctamente.")
        else:
            reason = "Ningún perfil pudo ejecutar la señal."
            event_bus.signalRejected.emit(
                SignalRejectedEvent(signal=signal, reason=reason)
            )
            event_bus.warning(reason)

        return executed


signal_engine = SignalEngine()
