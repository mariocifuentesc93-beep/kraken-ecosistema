from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TelegramChannel:
    id: Optional[int] = None
    telegram_account_id: Optional[int] = None
    chat_id: int = 0
    name: str = ""
    username: Optional[str] = None
    chat_type: str = "UNKNOWN"
    can_read: bool = True
    can_send: bool = False
    enabled: bool = True
    available: bool = True
    last_synced_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        object.__setattr__(self, "can_read", bool(self.can_read))
        object.__setattr__(self, "can_send", bool(self.can_send))
        object.__setattr__(self, "enabled", bool(self.enabled))
        object.__setattr__(self, "available", bool(self.available))

    @property
    def title(self):
        return self.name
