from dataclasses import dataclass
from typing import Optional


@dataclass
class Symbol:

    id: Optional[int] = None

    profile_id: int = 0

    symbol: str = ""

    mt5_symbol: str = ""

    description: str = ""

    aliases: str = ""

    enabled: bool = True

    risk: float = 1.0

    min_lot: float = 0.01

    max_lot: float = 100.0

    action: str = "trade"

    def __post_init__(self):

        self.enabled = bool(self.enabled)

        self.risk = float(self.risk)

        self.min_lot = float(self.min_lot)

        self.max_lot = float(self.max_lot)