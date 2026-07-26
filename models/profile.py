from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.signal_sources import normalize_signal_source_mode


@dataclass
class Profile:

    # =====================================================
    # IDENTIFICACIÓN
    # =====================================================

    id: Optional[int] = None

    name: str = ""

    description: str = ""

    # =====================================================
    # UI
    # =====================================================

    color: str = "#00C853"

    icon: str = "📈"

    # =====================================================
    # ESTADO
    # =====================================================

    active: bool = True

    enabled: bool = True

    operation_mode: str = "telegram"

    signal_source_mode: str = "TELEGRAM"

    # =====================================================
    # TELEGRAM
    # =====================================================

    telegram_account_id: Optional[int] = None

    telegram_channel_id: Optional[int] = None

    # =====================================================
    # MT5
    # =====================================================

    default_mt5_account: Optional[int] = None

    mt5_terminal_id: Optional[int] = None

    catalog_id: str = "BRIDGE_SYNTHETICS"

    magic_number: int = 10001

    comment: str = ""

    deviation: int = 20

    # =====================================================
    # RIESGO
    # =====================================================

    risk_enabled: bool = True

    risk_mode: str = "PERCENT"

    risk_percent: float = 2.0

    max_risk_percent: float = 5.0

    risk_amount: float = 0.0

    fixed_lot: float = 0.10

    min_lot: float = 0.01

    max_lot: float = 100.0

    max_daily_loss: float = 0.0

    max_daily_profit: float = 0.0

    max_drawdown: float = 0.0

    max_open_trades: int = 0

    # Minimum internal quality score (0-100) required for a signal.
    # Zero leaves score filtering disabled.
    min_signal_score: float = 0.0

    # =====================================================
    # EJECUCIÓN
    # =====================================================

    execution_mode: str = "OFF"

    tp_level: int = 1

    # Action applied once TP1 is reached.  LIVE execution remains blocked.
    tp1_management: str = "PROTECT_TP1"

    execute_market: bool = True

    allow_buy: bool = True

    allow_sell: bool = True

    # =====================================================
    # ESTADÍSTICAS
    # =====================================================

    total_operations: int = 0

    winning_operations: int = 0

    losing_operations: int = 0

    breakeven_operations: int = 0

    total_profit: float = 0.0

    total_loss: float = 0.0

    net_profit: float = 0.0

    win_rate: float = 0.0

    # =====================================================
    # AUDITORÍA
    # =====================================================

    created_at: Optional[str] = None

    updated_at: Optional[str] = None

    # =====================================================

    def __post_init__(self):

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not self.created_at:
            self.created_at = now

        if not self.updated_at:
            self.updated_at = now

        self.active = bool(self.active)
        self.enabled = bool(self.enabled)
        self.risk_enabled = bool(self.risk_enabled)
        self.execute_market = bool(self.execute_market)
        self.allow_buy = bool(self.allow_buy)
        self.allow_sell = bool(self.allow_sell)
        self.signal_source_mode = normalize_signal_source_mode(
            self.signal_source_mode
        )

        self.risk_percent = float(self.risk_percent)
        self.max_risk_percent = float(self.max_risk_percent)
        self.risk_amount = float(self.risk_amount)
        self.fixed_lot = float(self.fixed_lot)
        self.min_lot = float(self.min_lot)
        self.max_lot = float(self.max_lot)

        self.max_daily_loss = float(self.max_daily_loss)
        self.max_daily_profit = float(self.max_daily_profit)
        self.max_drawdown = float(self.max_drawdown)

        self.max_open_trades = int(self.max_open_trades)
        self.min_signal_score = float(self.min_signal_score)

        self.magic_number = int(self.magic_number)

        self.deviation = int(self.deviation)

    @property
    def is_active(self):

        return self.active and self.enabled

    @property
    def display_name(self):

        return f"{self.icon} {self.name}"

    def update_statistics(
        self,
        operations,
        wins,
        losses,
        breakeven,
        profit,
        loss,
    ):

        self.total_operations = operations
        self.winning_operations = wins
        self.losing_operations = losses
        self.breakeven_operations = breakeven

        self.total_profit = profit
        self.total_loss = loss
        self.net_profit = profit + loss

        if operations:
            self.win_rate = round(wins / operations * 100, 2)
        else:
            self.win_rate = 0.0
