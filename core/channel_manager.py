from database.channel_repository import (
    add_channel,
    get_channel,
    get_channels,
    enable_channel,
    disable_channel,
)


class ChannelManager:

    def add(self, chat_id, name):

        add_channel(chat_id, name)

    def get(self, chat_id):

        return get_channel(chat_id)

    def get_all(self):

        return get_channels()

    def enable(self, chat_id):

        return enable_channel(chat_id)

    def disable(self, chat_id):

        return disable_channel(chat_id)

    def exists(self, chat_id):

        return get_channel(chat_id) is not None

    def is_enabled(self, chat_id):

        channel = get_channel(chat_id)

        if channel is None:
            return False

        return channel["enabled"]


channel_manager = ChannelManager()