from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Signal:

    # =====================================================
    # IDENTIFICACIÓN
    # =====================================================

    id: Optional[int] = None

    source: str = "Telegram"

    chat_id: Optional[int] = None

    message_id: Optional[int] = None

    telegram_account_id: Optional[int] = None

    received_at: datetime = field(default_factory=datetime.now)

    # =====================================================
    # TRADING
    # =====================================================

    symbol: str = ""

    direction: str = ""

    entry: float = 0.0

    stop_loss: float = 0.0

    take_profits: List[float] = field(default_factory=list)

    # =====================================================
    # EJECUCIÓN
    # =====================================================

    profile_id: Optional[int] = None

    profile_name: str = ""

    profile_telegram_account_id: Optional[int] = None

    mt5_account_id: Optional[int] = None

    mt5_account_name: str = ""

    volume: float = 0.0

    # =====================================================
    # ESTADO
    # =====================================================

    score: float = 0.0

    status: str = "NEW"

    raw_message: str = ""

    metadata: Dict = field(default_factory=dict)

    # =====================================================
    # PROPIEDADES
    # =====================================================

    @property
    def tp1(self):

        return self.take_profits[0] if len(self.take_profits) > 0 else 0.0

    @property
    def tp2(self):

        return self.take_profits[1] if len(self.take_profits) > 1 else 0.0

    @property
    def tp3(self):

        return self.take_profits[2] if len(self.take_profits) > 2 else 0.0

    @property
    def risk(self):

        return abs(self.entry - self.stop_loss)

    @property
    def rr_tp1(self):

        if self.risk == 0:

            return 0.0

        return abs(self.tp1 - self.entry) / self.risk

    @property
    def rr_tp2(self):

        if self.risk == 0:

            return 0.0

        return abs(self.tp2 - self.entry) / self.risk

    @property
    def rr_tp3(self):

        if self.risk == 0:

            return 0.0

        return abs(self.tp3 - self.entry) / self.risk