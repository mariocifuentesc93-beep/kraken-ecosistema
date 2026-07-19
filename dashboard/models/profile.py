from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Profile:

    id: Optional[int] = None

    # Información general
    name: str = ""
    description: str = ""
    color: str = "#00C853"
    icon: str = "📈"

    # Estado
    active: bool = True

    # Modo de operación
    operation_mode: str = "telegram"
    # Valores:
    # telegram
    # manual
    # both

    # Auditoría
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if self.created_at is None:
            self.created_at = now

        if self.updated_at is None:
            self.updated_at = now