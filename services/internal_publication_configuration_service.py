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

    @staticmethod
    def _destination_name(destination):
        return str(
            destination.get("title")
            or destination.get("name")
            or destination.get("username")
            or destination["chat_id"]
        ).strip()

    @staticmethod
    def _destination_type(destination):
        explicit = str(
            destination.get("type")
            or destination.get("entity_type")
            or ""
        ).strip()
        if explicit:
            return explicit
        return "Canal" if destination.get("username") else "Grupo"

    def validate(self, enabled, telegram_account_id, chat_id):
        enabled = bool(enabled)
        if not enabled and telegram_account_id is None and chat_id is None:
            return InternalPublicationConfig()

        config = InternalPublicationConfig(
            enabled=enabled,
            telegram_account_id=telegram_account_id,
            telegram_output_chat_id=chat_id,
        )
        if enabled:
            config.validate()

        account = self._account_provider(config.telegram_account_id)
        if account is None or not getattr(account, "enabled", True):
            if enabled:
                raise ValueError("La cuenta Telegram seleccionada no existe.")
            return config

        destinations = self._destinations_provider(
            config.telegram_account_id
        )
        destination = next(
            (
                item
                for item in destinations
                if int(item["chat_id"]) == config.telegram_output_chat_id
            ),
            None,
        )
        if destination is None:
            if enabled:
                raise ValueError(
                    "El chat o canal no pertenece a la cuenta seleccionada."
                )
            return config

        return InternalPublicationConfig(
            enabled=enabled,
            telegram_account_id=config.telegram_account_id,
            telegram_output_chat_id=config.telegram_output_chat_id,
            destination_name=self._destination_name(destination),
            destination_type=self._destination_type(destination),
        )

    def save(self, enabled, telegram_account_id, chat_id):
        config = self.validate(enabled, telegram_account_id, chat_id)
        if config.enabled:
            account = self._account_provider(config.telegram_account_id)
            if account is None or not getattr(account, "enabled", True):
                raise ValueError("La cuenta Telegram seleccionada no existe.")
        return self._repository.save(config)
