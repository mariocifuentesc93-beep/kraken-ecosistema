from engine.profile_engine import profile_engine

from repositories.profile_repository import profile_repository

from core.event_bus import event_bus

from core.events import (
    SignalReceivedEvent,
    SignalRejectedEvent,
    SignalProcessedEvent,
    ProfileStartedEvent,
    ProfileFinishedEvent,
)


class SignalEngine:

    def __init__(self):

        self.running = False

    # ---------------------------------------------------------

    def start(self):

        self.running = True

        event_bus.log(
            "SignalEngine iniciado."
        )

    # ---------------------------------------------------------

    def stop(self):

        self.running = False

        event_bus.log(
            "SignalEngine detenido."
        )

    # ---------------------------------------------------------

    def process(
        self,
        signal,
        profile=None,
        chat_id=None,
        account_id=None,
    ):

        if not self.running:

            event_bus.warning(
                "SignalEngine detenido."
            )

            return False

        # -----------------------------------------------------
        # EVENTO
        # -----------------------------------------------------

        event_bus.signalReceived.emit(

            SignalReceivedEvent(

                signal=signal,

                chat_id=chat_id,

                telegram_account_id=account_id,

            )

        )

        print()
        print("=" * 60)
        print("🚀 SIGNAL ENGINE")
        print("=" * 60)

        # -----------------------------------------------------
        # ORIGEN
        # -----------------------------------------------------

        if chat_id is None:
            chat_id = getattr(signal, "chat_id", None)

        signal.chat_id = chat_id

        signal.telegram_account_id = account_id

        profiles = [profile] if profile is not None else (
            profile_repository.get_profiles_by_chat(chat_id)
        )

        if not profiles:

            event_bus.signalRejected.emit(

                SignalRejectedEvent(

                    signal=signal,

                    reason=f"No existen perfiles asociados al chat {chat_id}",

                )

            )

            event_bus.warning(

                f"No existen perfiles asociados al chat {chat_id}"

            )

            print(

                f"[SignalEngine] No existen perfiles asociados al chat {chat_id}"

            )

            return False

        executed = False

        # -----------------------------------------------------
        # PROCESAR PERFILES
        # -----------------------------------------------------

        for profile in profiles:

            if not getattr(profile, "enabled", True):

                continue

            event_bus.profileStarted.emit(

                ProfileStartedEvent(

                    profile=profile,

                    signal=signal,

                )

            )

            print()
            print(f"Perfil : {profile.name}")

            try:

                signal.profile_id = profile.id

            except Exception:

                pass

            result = profile_engine.process_signal(

                signal,

                profile,

            )

            event_bus.profileFinished.emit(

                ProfileFinishedEvent(

                    profile=profile,

                    signal=signal,

                    success=result,

                )

            )

            if result:

                executed = True

        # -----------------------------------------------------
        # RESULTADO
        # -----------------------------------------------------

        if executed:

            event_bus.signalProcessed.emit(

                SignalProcessedEvent(

                    signal=signal,

                )

            )

            event_bus.log(

                "La señal fue enviada correctamente."

            )

            print()
            print("✅ La señal fue enviada a uno o más perfiles.")

        else:

            event_bus.signalRejected.emit(

                SignalRejectedEvent(

                    signal=signal,

                    reason="Ningún perfil pudo ejecutar la señal.",

                )

            )

            event_bus.warning(

                "Ningún perfil pudo ejecutar la señal."

            )

            print()
            print("⚠ Ningún perfil ejecutó la señal.")

        return executed


signal_engine = SignalEngine()
