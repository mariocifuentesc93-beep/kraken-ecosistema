from database.database_manager import database_manager
from engine.kraken_engine import kraken_engine
from mt5.connector import mt5_connector
from telegram.account_manager import telegram_account_manager


def shutdown_application():
    """Stop background resources before Qt destroys widgets and exits."""
    kraken_engine.stop()
    telegram_account_manager.shutdown()
    if mt5_connector.connected:
        mt5_connector.disconnect()
    database_manager.close()
