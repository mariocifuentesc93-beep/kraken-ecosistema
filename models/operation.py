from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from models.signal import Signal
from models.profile import Profile
from models.mt5_account import MT5Account


@dataclass
class Operation:

    # =====================================================
    # IDENTIFICACIÓN
    # =====================================================

    id: Optional[int] = None

    signal: Optional[Signal] = None

    profile: Optional[Profile] = None

    account: Optional[MT5Account] = None

    # =====================================================
    # RELACIONES
    # =====================================================

    profile_id: Optional[int] = None

    mt5_account_id: Optional[int] = None

    telegram_account_id: Optional[int] = None

    # =====================================================
    # MT5
    # =====================================================

    ticket: Optional[int] = None

    position_id: Optional[int] = None

    deal_id: Optional[int] = None

    volume: float = 0.0

    magic: int = 0

    magic_number: int = 0

    comment: str = ""

    symbol: str = ""

    direction: str = ""

    # =====================================================
    # PRECIOS
    # =====================================================

    entry: float = 0.0

    entry_price: float = 0.0

    exit_price: float = 0.0

    stop_loss: float = 0.0

    take_profit: float = 0.0

    # =====================================================
    # ESTADO
    # =====================================================

    status: str = "PENDING"

    result: str = ""

    close_reason: Optional[str] = None

    # =====================================================
    # RESULTADOS
    # =====================================================

    profit: float = 0.0

    swap: float = 0.0

    commission: float = 0.0

    pips: float = 0.0

    rr: float = 0.0

    # =====================================================
    # TIEMPOS
    # =====================================================

    created_at: datetime = field(default_factory=datetime.now)

    opened_at: Optional[datetime] = None

    closed_at: Optional[datetime] = None

    updated_at: Optional[datetime] = None

    # =====================================================
    # CONTROL
    # =====================================================

    monitored: bool = False

    synchronized: bool = False

    partial_closed: bool = False

    break_even: bool = False

    trailing_stop: bool = False

    # =====================================================
    # CACHE
    # =====================================================

    profile_name: str = ""

    account_name: str = ""

    # =====================================================
    # EXTRA
    # =====================================================

    metadata: dict = field(default_factory=dict)

    # =====================================================
    # POST INIT
    # =====================================================

    def __post_init__(self):

        if self.signal:

            self.symbol = getattr(self.signal, "symbol", "")

            self.direction = getattr(self.signal, "direction", "")

            self.entry = getattr(
                self.signal,
                "entry",
                getattr(self.signal, "entry_price", 0.0),
            )

            self.entry_price = self.entry

            self.stop_loss = getattr(
                self.signal,
                "stop_loss",
                0.0,
            )

            tps = getattr(self.signal, "take_profits", [])

            if tps:

                self.take_profit = tps[0]

            self.telegram_account_id = getattr(
                self.signal,
                "telegram_account_id",
                None,
            )

        if self.profile:

            self.profile_id = getattr(
                self.profile,
                "id",
                None,
            )

            self.profile_name = getattr(
                self.profile,
                "name",
                "",
            )

        if self.account:

            self.mt5_account_id = getattr(
                self.account,
                "id",
                None,
            )

            self.account_name = getattr(
                self.account,
                "name",
                "",
            )

            self.magic_number = getattr(
                self.account,
                "custom_magic",
                getattr(
                    self.account,
                    "magic_number",
                    0,
                ),
            )

            self.magic = self.magic_number

            self.comment = getattr(
                self.account,
                "comment",
                "KRAKEN",
            )

    @property
    def account_id(self):
        return self.mt5_account_id

    @account_id.setter
    def account_id(self, value):
        self.mt5_account_id = value
