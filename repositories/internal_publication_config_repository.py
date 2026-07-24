from models.internal_publication_config import InternalPublicationConfig
from repositories.settings_repository import settings_repository


ENABLED_KEY = "internal.telegram_publication.enabled"
ACCOUNT_KEY = "internal.telegram_publication.telegram_account_id"
CHAT_KEY = "internal.telegram_publication.telegram_output_chat_id"


class InternalPublicationConfigRepository:
    """Persist the single INTERNAL publication destination in global settings."""

    def __init__(self, repository=None):
        self._settings = repository or settings_repository

    @staticmethod
    def _optional_integer(value):
        if value is None or isinstance(value, bool):
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            return int(text)
        except (TypeError, ValueError):
            return None

    def get(self):
        return InternalPublicationConfig(
            enabled=self._settings.get_bool(ENABLED_KEY, False),
            telegram_account_id=self._optional_integer(
                self._settings.get(ACCOUNT_KEY)
            ),
            telegram_output_chat_id=self._optional_integer(
                self._settings.get(CHAT_KEY)
            ),
        )

    def save(self, config):
        config.validate()
        self._settings.set(ENABLED_KEY, int(config.enabled))
        if config.telegram_account_id is None:
            self._settings.remove(ACCOUNT_KEY)
        else:
            self._settings.set(ACCOUNT_KEY, config.telegram_account_id)
        if config.telegram_output_chat_id is None:
            self._settings.remove(CHAT_KEY)
        else:
            self._settings.set(
                CHAT_KEY,
                config.telegram_output_chat_id,
            )
        return config


internal_publication_config_repository = (
    InternalPublicationConfigRepository()
)
