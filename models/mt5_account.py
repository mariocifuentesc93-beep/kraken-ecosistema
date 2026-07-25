from dataclasses import dataclass
from typing import Optional


@dataclass
class MT5Account:

    # =====================================================
    # IDENTIFICACIÓN
    # =====================================================

    id: Optional[int] = None

    name: str = ""

    description: str = ""

    # =====================================================
    # CONEXIÓN MT5
    # =====================================================

    login: int = 0

    password: str = ""

    server: str = ""

    terminal_path: str = ""

    mt5_terminal_id: Optional[int] = None

    # =====================================================
    # OPERACIÓN
    # =====================================================

    active: bool = True

    enabled: bool = True

    auto_connect: bool = True

    reconnect: bool = True

    execution_mode: str = "OFF"

    priority: int = 1

    # =====================================================
    # RIESGO
    # =====================================================

    risk_enabled: bool = True

    risk_mode: str = "PROFILE"

    risk_percent: float = 0.0

    risk_amount: float = 0.0

    fixed_lot: float = 0.0

    min_lot: float = 0.01

    max_lot: float = 100.0

    # =====================================================
    # MT5
    # =====================================================

    magic_number: int = 10001

    custom_magic: int = 0

    comment: str = "KRAKEN"

    deviation: int = 20

    # =====================================================
    # ESTADO
    # =====================================================

    connected: bool = False

    last_error: str = ""

    balance: float = 0.0

    equity: float = 0.0

    free_margin: float = 0.0

    # =====================================================
    # ESTADÍSTICAS
    # =====================================================

    total_operations: int = 0

    total_wins: int = 0

    total_losses: int = 0

    total_profit: float = 0.0

    win_rate: float = 0.0

    # =====================================================
    # PROPIEDADES
    # =====================================================

    @property
    def magic(self):

        return self.custom_magic or self.magic_number

    @property
    def is_enabled(self):

        return self.active and self.enabled

    # =====================================================
    # MÉTODOS
    # =====================================================

    def update_account_info(
        self,
        balance,
        equity,
        free_margin,
    ):

        self.balance = float(balance)
        self.equity = float(equity)
        self.free_margin = float(free_margin)

    def set_connection_status(
        self,
        connected,
        error="",
    ):

        self.connected = bool(connected)
        self.last_error = error

    def update_statistics(
        self,
        operations=0,
        wins=0,
        losses=0,
        profit=0.0,
    ):

        self.total_operations = operations
        self.total_wins = wins
        self.total_losses = losses
        self.total_profit = profit

        if operations > 0:

            self.win_rate = round(
                (wins / operations) * 100,
                2,
            )

        else:

            self.win_rate = 0.0
