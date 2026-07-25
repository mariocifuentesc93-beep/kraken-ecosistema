from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


class SignalIdentityError(ValueError):
    """La identidad de una señal no es válida para persistencia."""


def _normalize_source(value: str) -> str:
    return (value or "TELEGRAM").strip().upper()


def _telegram_integer(value, field_name: str) -> int:
    if isinstance(value, bool):
        raise SignalIdentityError(
            f"{field_name} no acepta valores booleanos"
        )
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        normalized = value.strip()
        if normalized and (
            normalized.isdigit()
            or (
                normalized[0] in "+-"
                and normalized[1:].isdigit()
            )
        ):
            return int(normalized)
    raise SignalIdentityError(
        f"{field_name} debe ser un entero válido"
    )


def _internal_external_id(value) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise SignalIdentityError(
            "external_signal_id debe ser texto o entero"
        )
    normalized = str(value).strip()
    if not normalized:
        raise SignalIdentityError(
            "external_signal_id es obligatorio para INTERNAL"
        )
    return normalized


def normalize_internal_symbol(value) -> str:
    """Normaliza el símbolo operativo usado en la identidad INTERNAL."""
    if not isinstance(value, str):
        raise SignalIdentityError(
            "symbol debe ser texto para INTERNAL"
        )
    normalized = value.strip().upper()
    if not normalized:
        raise SignalIdentityError(
            "symbol es obligatorio para INTERNAL"
        )
    if ":" in normalized or any(
        ord(character) < 32
        for character in normalized
    ):
        raise SignalIdentityError(
            "symbol contiene caracteres no permitidos para INTERNAL"
        )
    # Known catalog names use the same canonical identity in every source.
    # Unknown operational symbols retain the legacy uppercase representation.
    from config.symbols import normalize_symbol

    return normalize_symbol(normalized) or normalized


def build_internal_idempotency_key(symbol, external_signal_id) -> str:
    """Construye la única identidad canónica admitida para INTERNAL."""
    normalized_symbol = normalize_internal_symbol(symbol)
    normalized_external_id = _internal_external_id(external_signal_id)
    return f"INTERNAL:{normalized_symbol}:{normalized_external_id}"


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
    market_execution: bool = False

    raw_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "NEW"
    score: float = 0.0
    rejection_reason: str = ""
    execution_decision: str = ""

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
        if "market_execution" in self.metadata:
            self.market_execution = bool(
                self.metadata["market_execution"]
            )
        elif self.market_execution:
            self.metadata["market_execution"] = self.market_execution
        self.received_at = self._as_datetime(
            self.received_at,
            default=datetime.now(),
        )
        self.detected_at = self._as_datetime(self.detected_at)

        if (
            self.external_signal_id is not None
            and not isinstance(self.external_signal_id, bool)
            and isinstance(self.external_signal_id, (str, int))
        ):
            self.external_signal_id = str(self.external_signal_id).strip()

        if self.idempotency_key is None:
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
            try:
                account_id = _telegram_integer(
                    self.telegram_account_id,
                    "telegram_account_id",
                )
                chat_id = _telegram_integer(self.chat_id, "chat_id")
                message_id = _telegram_integer(
                    self.message_id,
                    "message_id",
                )
            except SignalIdentityError:
                return None
            return f"TELEGRAM:{account_id}:{chat_id}:{message_id}"

        if self.source == "INTERNAL":
            try:
                return build_internal_idempotency_key(
                    self.symbol,
                    self.external_signal_id,
                )
            except SignalIdentityError:
                return None

        return None

    def validate_persistent_identity(self) -> str:
        """Valida la fuente y reemplaza la clave por su forma canónica."""
        self.source = _normalize_source(self.source)
        manual_key = self.idempotency_key
        if manual_key is not None:
            manual_key = str(manual_key).strip()
            if not manual_key:
                raise SignalIdentityError(
                    "idempotency_key no puede estar vacía"
                )

        if self.source == "TELEGRAM":
            self.telegram_account_id = _telegram_integer(
                self.telegram_account_id,
                "telegram_account_id",
            )
            self.chat_id = _telegram_integer(self.chat_id, "chat_id")
            self.message_id = _telegram_integer(
                self.message_id,
                "message_id",
            )
            canonical_key = (
                f"TELEGRAM:{self.telegram_account_id}:"
                f"{self.chat_id}:{self.message_id}"
            )
        elif self.source == "INTERNAL":
            self.symbol = normalize_internal_symbol(self.symbol)
            external_id = _internal_external_id(
                self.external_signal_id
            )
            self.external_signal_id = external_id
            canonical_key = build_internal_idempotency_key(
                self.symbol,
                external_id,
            )
        elif self.source == "LEGACY":
            raise SignalIdentityError(
                "LEGACY está reservado para la migración"
            )
        else:
            raise SignalIdentityError(
                f"Fuente de señal no soportada: {self.source!r}"
            )

        if manual_key is not None and manual_key != canonical_key:
            raise SignalIdentityError(
                "idempotency_key manual no coincide con la identidad canónica"
            )

        self.idempotency_key = canonical_key
        return canonical_key

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
