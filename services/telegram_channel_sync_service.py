from repositories.telegram_account_repository import telegram_account_repository
from repositories.telegram_channel_repository import telegram_channel_repository
from telegram.account_manager import telegram_account_manager


class TelegramChannelSyncService:
    def __init__(self, account_repository=None, channel_repository=None, account_manager=None):
        self._accounts = account_repository or telegram_account_repository
        self._channels = channel_repository or telegram_channel_repository
        self._manager = account_manager or telegram_account_manager

    async def synchronize(self, account_id):
        account = self._accounts.get_by_id(account_id)
        if account is None:
            raise ValueError("La cuenta Telegram seleccionada no existe.")
        if not account.authorized:
            raise RuntimeError("La cuenta Telegram no está autorizada.")
        dialogs = await self._manager.list_dialog_catalog(account_id)
        return self._channels.synchronize(account_id, dialogs)
