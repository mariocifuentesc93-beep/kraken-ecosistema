from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class TelegramAccount:

    # =====================================================
    # IDENTIFICACIÓN
    # =====================================================

    id: Optional[int] = None

    # =====================================================
    # CUENTA
    # =====================================================

    name: str = ""

    phone: str = ""

    api_id: int = 0

    api_hash: str = ""

    session_name: str = ""

    # =====================================================
    # ESTADO
    # =====================================================

    enabled: bool = True

    auto_connect: bool = True

    connected: bool = False

    authorized: bool = False

    last_error: str = ""

    # =====================================================
    # INFORMACIÓN
    # =====================================================

    user_id: Optional[int] = None

    username: str = ""

    first_name: str = ""

    last_name: str = ""

    # =====================================================
    # AUDITORÍA
    # =====================================================

    created_at: Optional[str] = None

    updated_at: Optional[str] = None

    def __post_init__(self):

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if self.created_at is None:
            self.created_at = now

        if self.updated_at is None:
            self.updated_at = now

        self.enabled = bool(self.enabled)
        self.auto_connect = bool(self.auto_connect)
        self.connected = bool(self.connected)
        self.authorized = bool(self.authorized)

        self.api_id = int(self.api_id) if self.api_id else 0

    @property
    def display_name(self):

        if self.name:

            return self.name

        if self.phone:

            return self.phone

        return "Telegram"

    @property
    def full_name(self):

        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_ready(self):

        return (
            self.enabled
            and self.authorized
            and self.connected
        )