from models.internal_publication_config import InternalPublicationConfig


class InternalPublicationConfigurationService:
    """Validate the global destination against existing Kraken Telegram data."""

    def __init__(
        self,
        repository,
        account_provider,
        destinations_provider,
    ):
        self._repository = repository
        self._account_provider = account_provider
        self._destinations_provider = destinations_provider

    def get(self):
        return self._repository.get()

    def save(self, enabled, telegram_account_id, chat_id):
        config = InternalPublicationConfig(
            enabled=bool(enabled),
            telegram_account_id=telegram_account_id,
            telegram_output_chat_id=chat_id,
        )
        config.validate()
        if config.enabled:
            account = self._account_provider(config.telegram_account_id)
            if account is None or not getattr(account, "enabled", True):
                raise ValueError("La cuenta Telegram seleccionada no existe.")
            destinations = self._destinations_provider(
                config.telegram_account_id
            )
            if not any(
                int(item["chat_id"]) == config.telegram_output_chat_id
                for item in destinations
            ):
                raise ValueError(
                    "El chat o canal no pertenece a la cuenta seleccionada."
                )
        return self._repository.save(config)
