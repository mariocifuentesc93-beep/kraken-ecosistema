from dataclasses import dataclass
from typing import Optional


@dataclass
class TelegramChannel:

    id: Optional[int] = None

    profile_id: int = 0

    account_id: int = 0

    chat_id: int = 0

    title: str = ""

    username: str = ""

    enabled: bool = True

    priority: int = 1