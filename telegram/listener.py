from telethon import events

from core.signal_parser import parse_signal
from core.signal_validator import validate_signal

from engine.kraken_engine import kraken_engine

from repositories.profile_telegram_repository import (
    profile_telegram_channel_repository,
)


def register_telegram_listener(client):

    @client.on(events.NewMessage)
    async def new_message_handler(event):

        message = event.message
        text = message.message or ""
        chat_id = int(event.chat_id)

        print()
        print("=" * 60)
        print("📨 NUEVO MENSAJE")
        print("=" * 60)
        print(f"Chat ID: {chat_id}")

        signal = parse_signal(text)

        if signal is None:

            print("⚪ El mensaje no corresponde a una señal.")

            return

        signal.chat_id = chat_id
        signal.message_id = message.id

        valid, errors = validate_signal(signal)

        if not valid:

            print("❌ Señal rechazada")

            for error in errors:
                print(f"   • {error}")

            return

        profiles = (
            profile_telegram_channel_repository.get_profiles(chat_id)
        )

        if not profiles:

            print("⚠️ No hay perfiles asociados a este canal.")

            return

        print(f"✅ Señal enviada a {len(profiles)} perfil(es).")

        for profile in profiles:

            kraken_engine.process_signal(
                signal=signal,
                profile=profile,
            )