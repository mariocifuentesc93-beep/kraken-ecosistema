from dataclasses import dataclass
from typing import Optional


@dataclass
class Symbol:

    id: Optional[int] = None

    profile_id: int = 0

    enabled: bool = True

    symbol: str = ""

    description: str = ""

    aliases: str = ""

    risk: float = 1.0

    min_lot: float = 0.01

    max_lot: float = 100.0

    action: str = "trade"