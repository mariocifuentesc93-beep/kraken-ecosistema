from dataclasses import dataclass


@dataclass(frozen=True)
class InternalPublicationConfig:
    """Global destination used for every INTERNAL Telegram publication."""

    enabled: bool = False
    telegram_account_id: int | None = None
    telegram_output_chat_id: int | None = None
    destination_name: str | None = None
    destination_type: str | None = None

    def validate(self):
        if not self.enabled:
            return self
        if (
            isinstance(self.telegram_account_id, bool)
            or not isinstance(self.telegram_account_id, int)
            or self.telegram_account_id <= 0
        ):
            raise ValueError("Seleccione una cuenta Telegram válida.")
        if (
            isinstance(self.telegram_output_chat_id, bool)
            or not isinstance(self.telegram_output_chat_id, int)
            or self.telegram_output_chat_id == 0
        ):
            raise ValueError("Seleccione un chat o canal válido.")
        return self
