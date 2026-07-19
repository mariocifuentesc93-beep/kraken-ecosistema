from telethon import events

from core.signal_pipeline import process_signal_message
from repositories.profile_telegram_repository import profile_telegram_channel_repository


def register_telegram_listener(client):
    @client.on(events.NewMessage)
    async def new_message_handler(event):
        message = event.message
        text = message.message or ""
        chat_id = int(event.chat_id)
        profiles = profile_telegram_channel_repository.get_profiles(chat_id)

        # Every source message produces a persisted decision. No listener path
        # invokes the execution engine during connectivity validation.
        if not profiles:
            process_signal_message(text, chat_id=chat_id, source="Telegram")
            return
        for profile in profiles:
            process_signal_message(
                text,
                chat_id=chat_id,
                account_id=getattr(profile, "telegram_account_id", None),
                profile=profile,
                source="Telegram",
            )
