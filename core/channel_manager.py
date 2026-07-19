from repositories.profile_telegram_repository import (
    profile_telegram_channel_repository,
)


class ChannelManager:

    def add(self, chat_id, name, profile_id=None, account_id=None):
        return profile_telegram_channel_repository.create_channel(
            chat_id=chat_id,
            title=name,
            profile_id=profile_id,
            account_id=account_id,
        )

    def get(self, chat_id):

        return profile_telegram_channel_repository.get_channel(chat_id)

    def get_all(self):

        return profile_telegram_channel_repository.get_channels()

    def enable(self, chat_id):

        return profile_telegram_channel_repository.set_channel_enabled(
            chat_id,
            True,
        )

    def disable(self, chat_id):

        return profile_telegram_channel_repository.set_channel_enabled(
            chat_id,
            False,
        )

    def exists(self, chat_id):

        return self.get(chat_id) is not None

    def is_enabled(self, chat_id):

        channel = self.get(chat_id)

        if channel is None:
            return False

        return channel["enabled"]


channel_manager = ChannelManager()
