from copy import deepcopy
from inspect import signature

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

    def _get_profiles(self, signal, account_id, chat_id):
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
            from repositories.profile_telegram_repository import (
                profile_telegram_channel_repository,
            )
            self._profiles_provider = (
                profile_telegram_channel_repository.get_profiles
            )

        parameters = signature(self._profiles_provider).parameters
        if len(parameters) >= 2:
            return self._profiles_provider(account_id, chat_id)
        # Compatibility for injected Phase 0 test doubles.
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
        routed_profiles=None,
    ):
        """
        Procesa una señal normalizada y ya persistida.

        Este método es el único responsable de resolver los perfiles asociados
        al chat. Cada perfil recibe una copia independiente del Signal.
        """
        original_metadata = deepcopy(signal.metadata)
        original_profile_id = signal.profile_id
        original_profile_name = signal.profile_name
        original_reason = signal.rejection_reason
        original_decision = signal.execution_decision

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

        profiles = self._get_profiles(signal, account_id, chat_id)
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
            signal.rejection_reason = reason
            signal.execution_decision = "REJECTED"
            signal.metadata["failure_stage"] = "PROFILE_ROUTING"
            signal.metadata["rejection_reason"] = reason
            signal.metadata["execution_decision"] = "REJECTED"
            return False

        executed = False
        routing_attempts = []
        successful_profiles = []

        for profile in profiles:
            if not getattr(profile, "enabled", True):
                continue

            profile_signal = deepcopy(signal)
            profile_signal.profile_id = profile.id
            profile_signal.profile_name = profile.name

            valid, errors = self._validate(profile_signal, profile)

            if not valid:
                reason = "; ".join(errors)
                profile_signal.rejection_reason = reason
                profile_signal.execution_decision = "REJECTED"
                profile_signal.metadata["failure_stage"] = "VALIDATION"
                profile_signal.metadata["rejection_reason"] = reason
                profile_signal.metadata["execution_decision"] = "REJECTED"
                routing_attempts.append(
                    {
                        "profile_id": profile.id,
                        "profile_name": profile.name,
                        "execution_mode": getattr(
                            profile, "execution_mode", ""
                        ),
                        "success": False,
                        "failure_stage": "VALIDATION",
                        "reason": reason,
                        "decision": "REJECTED",
                    }
                )
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
            routing_attempts.append(
                {
                    "profile_id": profile.id,
                    "profile_name": profile.name,
                    "execution_mode": getattr(
                        profile, "execution_mode", ""
                    ),
                    "success": bool(result),
                    "failure_stage": profile_signal.metadata.get(
                        "failure_stage", ""
                    ),
                    "reason": profile_signal.rejection_reason,
                    "decision": profile_signal.execution_decision,
                    "traceback": profile_signal.metadata.get(
                        "traceback", ""
                    ),
                }
            )

            if result:
                executed = True
                successful_profiles.append(profile)
                if routed_profiles is not None:
                    routed_profiles.append(profile)

        if executed:
            if successful_profiles:
                signal.profile_id = successful_profiles[0].id
                signal.profile_name = successful_profiles[0].name
            signal.rejection_reason = ""
            signal.execution_decision = (
                "SIMULATED"
                if routing_attempts
                and all(
                    item["execution_mode"] == "SIMULATION"
                    for item in routing_attempts
                    if item["success"]
                )
                else "EXECUTED"
            )
            signal.metadata["routing_attempts"] = routing_attempts
            signal.metadata["routed_profiles"] = [
                {
                    "id": profile.id,
                    "name": profile.name,
                    "execution_mode": getattr(
                        profile, "execution_mode", ""
                    ),
                }
                for profile in successful_profiles
            ]
            signal.metadata["execution_decision"] = signal.execution_decision
            event_bus.signalProcessed.emit(
                SignalProcessedEvent(signal=signal)
            )
            event_bus.log("La señal fue enviada correctamente.")
        else:
            reason = next(
                (
                    item["reason"]
                    for item in routing_attempts
                    if item["reason"]
                ),
                "Ningún perfil pudo ejecutar la señal.",
            )
            signal.rejection_reason = reason
            signal.execution_decision = "REJECTED"
            signal.metadata["routing_attempts"] = routing_attempts
            signal.metadata["failure_stage"] = next(
                (
                    item["failure_stage"]
                    for item in routing_attempts
                    if item["failure_stage"]
                ),
                "ROUTING",
            )
            signal.metadata["rejection_reason"] = reason
            signal.metadata["execution_decision"] = "REJECTED"
            event_bus.signalRejected.emit(
                SignalRejectedEvent(signal=signal, reason=reason)
            )
            event_bus.warning(reason)

        if signal.id is None and signal.source == "TELEGRAM":
            signal.metadata = original_metadata
            signal.profile_id = original_profile_id
            signal.profile_name = original_profile_name
            signal.rejection_reason = original_reason
            signal.execution_decision = original_decision

        return executed


signal_engine = SignalEngine()
