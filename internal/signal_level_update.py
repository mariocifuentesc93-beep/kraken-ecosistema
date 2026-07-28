"""Contrato inmutable para cambios de niveles de una señal INTERNAL."""

from dataclasses import dataclass
from datetime import datetime

from models.signal import build_internal_idempotency_key


@dataclass(frozen=True)
class InternalSignalLevelUpdate:
    symbol: str
    external_signal_id: str
    direction: str
    previous_stop_loss: float
    stop_loss: float
    previous_take_profits: tuple[float, ...]
    take_profits: tuple[float, ...]
    detected_at: datetime

    @property
    def signal_key(self):
        return build_internal_idempotency_key(
            self.symbol, self.external_signal_id
        )

    @property
    def changes(self):
        result = {}
        if self.previous_stop_loss != self.stop_loss:
            result["SL"] = (self.previous_stop_loss, self.stop_loss)
        for index, value in enumerate(self.take_profits[:3], 1):
            previous = (
                self.previous_take_profits[index - 1]
                if len(self.previous_take_profits) >= index
                else 0.0
            )
            if previous != value:
                result[f"TP{index}"] = (previous, value)
        return result
