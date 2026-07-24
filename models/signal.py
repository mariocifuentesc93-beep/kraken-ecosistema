from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


def _normalize_source(value: str) -> str:
    return (value or "TELEGRAM").strip().upper()


@dataclass
class Signal:
    """Contrato unificado de una señal, independiente de su fuente."""

    id: Optional[int] = None
    source: str = "TELEGRAM"
    external_signal_id: Optional[str] = None
    idempotency_key: Optional[str] = None

    telegram_account_id: Optional[int] = None
    chat_id: Optional[int] = None
    message_id: Optional[int] = None

    received_at: datetime = field(default_factory=datetime.now)
    detected_at: Optional[datetime] = None

    symbol: str = ""
    direction: str = ""
    entry: float = 0.0
    stop_loss: float = 0.0
    take_profits: List[float] = field(default_factory=list)

    raw_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "NEW"
    score: float = 0.0

    # Contexto de ejecución heredado. No forma parte de la identidad persistente.
    profile_id: Optional[int] = None
    profile_name: str = ""
    profile_telegram_account_id: Optional[int] = None
    mt5_account_id: Optional[int] = None
    mt5_account_name: str = ""
    volume: float = 0.0

    def __post_init__(self) -> None:
        self.source = _normalize_source(self.source)
        self.direction = (self.direction or "").strip().upper()
        self.take_profits = [
            float(value)
            for value in (self.take_profits or [])
            if value is not None
        ]
        self.metadata = dict(self.metadata or {})
        self.received_at = self._as_datetime(
            self.received_at,
            default=datetime.now(),
        )
        self.detected_at = self._as_datetime(self.detected_at)

        if self.external_signal_id is not None:
            self.external_signal_id = str(self.external_signal_id).strip()

        if not self.idempotency_key:
            self.idempotency_key = self.build_idempotency_key()

    @staticmethod
    def _as_datetime(value, default=None) -> Optional[datetime]:
        if value is None or value == "":
            return default
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

    def build_idempotency_key(self) -> Optional[str]:
        if self.source == "TELEGRAM":
            identity = (
                self.telegram_account_id,
                self.chat_id,
                self.message_id,
            )
            if all(value is not None for value in identity):
                return "TELEGRAM:{0}:{1}:{2}".format(*identity)
            return None

        if self.source == "INTERNAL" and self.external_signal_id:
            return f"INTERNAL:{self.external_signal_id}"

        return None

    @property
    def tp1(self) -> float:
        return self.take_profits[0] if len(self.take_profits) > 0 else 0.0

    @property
    def tp2(self) -> float:
        return self.take_profits[1] if len(self.take_profits) > 1 else 0.0

    @property
    def tp3(self) -> float:
        return self.take_profits[2] if len(self.take_profits) > 2 else 0.0

    @property
    def created_at(self) -> datetime:
        """Alias de compatibilidad: el contrato canónico usa received_at."""
        return self.received_at

    @created_at.setter
    def created_at(self, value) -> None:
        self.received_at = self._as_datetime(value, default=datetime.now())

    @property
    def market_execution(self) -> bool:
        """Compatibilidad con consumidores heredados sin duplicar columnas."""
        return bool(self.metadata.get("market_execution", False))

    @market_execution.setter
    def market_execution(self, value) -> None:
        self.metadata["market_execution"] = bool(value)

    @property
    def risk(self) -> float:
        return abs(self.entry - self.stop_loss)

    @property
    def rr_tp1(self) -> float:
        return abs(self.tp1 - self.entry) / self.risk if self.risk else 0.0

    @property
    def rr_tp2(self) -> float:
        return abs(self.tp2 - self.entry) / self.risk if self.risk else 0.0

    @property
    def rr_tp3(self) -> float:
        return abs(self.tp3 - self.entry) / self.risk if self.risk else 0.0
