import asyncio

from database.database_manager import database_manager
from core.config_service import load_active_config

from telegram.client import client
from telegram.account_service import telegram_account_service
from telegram.listener import register_telegram_listener

from engine.kraken_engine import kraken_engine


async def main():

    print("Inicializando Base de Datos...")
    database_manager.initialize()

    print("Cargando configuración...")

    if not load_active_config():
        print("No existe un perfil activo.")
        return

    if client is None:
        print("No existe una cuenta de Telegram configurada.")
        return

    print("Conectando a Telegram...")

    await client.start(
        phone=telegram_account_service.get_phone()
    )

    register_telegram_listener(client)

    print("Inicializando Kraken Engine...")
    kraken_engine.start()

    print("=" * 50)
    print("             KRAKEN BOT")
    print("=" * 50)

    me = await client.get_me()

    print(f"Usuario : {me.first_name}")

    if getattr(me, "last_name", None):
        print(f"Apellido: {me.last_name}")

    print(f"ID      : {me.id}")

    if getattr(me, "username", None):
        print(f"Usuario TG: @{me.username}")

    print("=" * 50)

    print("📡 Escuchando Telegram...")
    print("CTRL + C para salir")
    print("=" * 50)

    try:

        await client.run_until_disconnected()

    except KeyboardInterrupt:

        print("\nDeteniendo Kraken...")

    finally:

        kraken_engine.stop()

        if client.is_connected():
            await client.disconnect()

        print("Kraken detenido.")


if __name__ == "__main__":

    asyncio.run(main())