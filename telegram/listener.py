from telethon import events

from core.signal_parser import parse_signal


def register_telegram_listener(
    client,
    account_id=None,
    signal_processor=None,
):
    """
    Registra el adaptador de entrada Telegram.

    El listener solo normaliza el mensaje y conserva su contexto de origen.
    SignalEngine es responsable de seleccionar y validar los perfiles.

    ``signal_processor`` permite probar este adaptador sin iniciar KrakenEngine.
    """

    if signal_processor is None:
        from engine.kraken_engine import kraken_engine
        signal_processor = kraken_engine.process_telegram_signal

    @client.on(events.NewMessage)
    async def new_message_handler(event):

        message = event.message
        text = message.message or ""
        chat_id = int(event.chat_id)

        print()
        print("=" * 60)
        print("NUEVO MENSAJE TELEGRAM")
        print("=" * 60)
        print(f"Chat ID: {chat_id}")

        signal = parse_signal(text)

        if signal is None:
            print("El mensaje no corresponde a una señal.")
            return

        signal.source = "TELEGRAM"
        signal.telegram_account_id = account_id
        signal.chat_id = chat_id
        signal.message_id = message.id
        signal.idempotency_key = signal.build_idempotency_key()

        signal_processor(
            signal=signal,
            chat_id=chat_id,
            account_id=account_id,
        )

    return new_message_handler
