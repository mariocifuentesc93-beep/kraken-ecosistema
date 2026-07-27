"""Pure, account-scoped position sizing for every execution mode."""

from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_FLOOR


ABSOLUTE_MAX_RISK_PERCENT = 10.0
MAX_ORDERS_PER_SIGNAL = 10


class PositionSizingError(ValueError):
    pass


@dataclass(frozen=True)
class PositionSizingResult:
    allowed: bool
    mode: str
    volume: float = 0.0
    requested_risk: float = 0.0
    estimated_risk_money: float = 0.0
    estimated_risk_percent: float = 0.0
    stop_distance: float = 0.0
    money_per_price_unit: float = 0.0
    raw_volume: float = 0.0
    normalized_volume: float = 0.0
    balance: float = 0.0
    equity: float = 0.0
    order_volumes: tuple = ()
    order_count: int = 1
    max_order_volume: float = 0.0
    reason: str = ""

    def to_dict(self):
        return asdict(self)


class PositionSizingService:
    def __init__(self, absolute_max_risk_percent=ABSOLUTE_MAX_RISK_PERCENT):
        self.absolute_max_risk_percent = float(absolute_max_risk_percent)

    @staticmethod
    def _value(source, name, default=0.0):
        if isinstance(source, dict):
            return source.get(name, default)
        return getattr(source, name, default)

    @staticmethod
    def _floor_to_step(value, step):
        value_d = Decimal(str(value))
        step_d = Decimal(str(step))
        steps = (value_d / step_d).to_integral_value(rounding=ROUND_FLOOR)
        return float(steps * step_d)

    @staticmethod
    def _split_volume(total, minimum, maximum, step):
        step_d = Decimal(str(step))
        total_units = int(
            (Decimal(str(total)) / step_d).to_integral_value(
                rounding=ROUND_FLOOR
            )
        )
        minimum_units = int(
            (Decimal(str(minimum)) / step_d).to_integral_value(
                rounding=ROUND_FLOOR
            )
        )
        if Decimal(minimum_units) * step_d < Decimal(str(minimum)):
            minimum_units += 1
        maximum_units = int(
            (Decimal(str(maximum)) / step_d).to_integral_value(
                rounding=ROUND_FLOOR
            )
        )
        if minimum_units <= 0 or maximum_units < minimum_units:
            raise PositionSizingError(
                "Los límites por orden no permiten un volumen válido."
            )
        order_count = (
            total_units + maximum_units - 1
        ) // maximum_units
        if order_count > MAX_ORDERS_PER_SIGNAL:
            raise PositionSizingError(
                "El volumen requiere más de 10 órdenes para una sola señal."
            )
        if total_units < order_count * minimum_units:
            raise PositionSizingError(
                "El volumen residual queda por debajo del mínimo permitido."
            )

        remaining = total_units
        volumes = []
        for index in range(order_count):
            remaining_orders = order_count - index - 1
            units = min(
                maximum_units,
                remaining - (remaining_orders * minimum_units),
            )
            volumes.append(float(Decimal(units) * step_d))
            remaining -= units
        return tuple(volumes)

    def calculate(self, profile, account, symbol, direction, entry, stop_loss,
                  symbol_info):
        mode = str(self._value(profile, "risk_mode", "PERCENT")).upper()
        if mode == "FIXED":
            mode = "LOT"
        if not bool(self._value(profile, "risk_enabled", True)):
            mode = "LOT"

        balance = float(self._value(account, "balance", 0.0) or 0.0)
        equity = float(self._value(account, "equity", balance) or balance)
        capital = equity if equity > 0 else balance
        if capital <= 0:
            raise PositionSizingError(
                "La cuenta destino no tiene balance/equity válido."
            )

        entry = float(entry or 0.0)
        stop_loss = float(stop_loss or 0.0)
        if not stop_loss:
            raise PositionSizingError("La señal no contiene Stop Loss.")
        distance = abs(entry - stop_loss)
        if entry <= 0 or distance <= 0:
            raise PositionSizingError("Entrada y Stop Loss no forman una distancia válida.")
        side = str(direction).upper()
        if side == "BUY" and stop_loss >= entry:
            raise PositionSizingError("En BUY el Stop Loss debe estar debajo de la entrada.")
        if side == "SELL" and stop_loss <= entry:
            raise PositionSizingError("En SELL el Stop Loss debe estar encima de la entrada.")
        if side not in {"BUY", "SELL"}:
            raise PositionSizingError("La dirección debe ser BUY o SELL.")

        tick_size = float(self._value(symbol_info, "trade_tick_size", 0.0) or 0.0)
        tick_value = float(self._value(symbol_info, "trade_tick_value", 0.0) or 0.0)
        if tick_size <= 0:
            raise PositionSizingError("El símbolo no tiene tick_size válido.")
        if tick_value <= 0:
            raise PositionSizingError("El símbolo no tiene tick_value válido.")
        volume_min = float(self._value(symbol_info, "volume_min", 0.0) or 0.0)
        volume_max = float(self._value(symbol_info, "volume_max", 0.0) or 0.0)
        volume_step = float(self._value(symbol_info, "volume_step", 0.0) or 0.0)
        if volume_min <= 0 or volume_max < volume_min or volume_step <= 0:
            raise PositionSizingError("Los límites de volumen del símbolo no son válidos.")

        profile_min = float(self._value(profile, "min_lot", volume_min) or volume_min)
        profile_max = float(self._value(profile, "max_lot", volume_max) or volume_max)
        effective_min = max(volume_min, profile_min)
        effective_max = min(volume_max, profile_max)
        if effective_max < effective_min:
            raise PositionSizingError("Los límites de volumen del perfil son incompatibles.")

        max_percent = float(self._value(profile, "max_risk_percent", 5.0) or 0.0)
        if max_percent <= 0 or max_percent > self.absolute_max_risk_percent:
            raise PositionSizingError("El riesgo máximo porcentual del perfil no es válido.")
        maximum_money = capital * max_percent / 100.0
        money_per_unit = tick_value / tick_size
        loss_per_lot = distance * money_per_unit

        if mode == "PERCENT":
            requested = float(self._value(profile, "risk_percent", 0.0) or 0.0)
            if requested <= 0:
                raise PositionSizingError("risk_percent debe ser mayor que 0.")
            if requested > max_percent:
                raise PositionSizingError("risk_percent supera max_risk_percent.")
            requested_money = capital * requested / 100.0
            raw = requested_money / loss_per_lot
        elif mode == "AMOUNT":
            requested = float(self._value(profile, "risk_amount", 0.0) or 0.0)
            if requested <= 0:
                raise PositionSizingError("risk_amount debe ser mayor que 0.")
            if requested > maximum_money:
                raise PositionSizingError("risk_amount supera el riesgo máximo del perfil.")
            requested_money = requested
            raw = requested_money / loss_per_lot
        elif mode == "LOT":
            requested = float(self._value(profile, "fixed_lot", 0.0) or 0.0)
            if requested <= 0:
                raise PositionSizingError("fixed_lot debe ser mayor que 0.")
            raw = requested
            requested_money = raw * loss_per_lot
        else:
            raise PositionSizingError(f"Modo de riesgo no soportado: {mode}.")

        if raw < effective_min:
            raise PositionSizingError(
                "El volumen calculado está por debajo del mínimo; no se elevará porque aumentaría el riesgo."
            )
        broker_capacity = volume_max * MAX_ORDERS_PER_SIGNAL
        if raw > broker_capacity + 1e-9:
            raise PositionSizingError(
                "El volumen requiere más de 10 órdenes para una sola señal."
            )
        total_maximum = min(profile_max, broker_capacity)
        normalized = min(
            self._floor_to_step(raw, volume_step),
            total_maximum,
        )
        if normalized < effective_min:
            raise PositionSizingError("No existe un volumen válido dentro de los límites.")
        order_volumes = self._split_volume(
            normalized,
            effective_min,
            volume_max,
            volume_step,
        )
        estimated = normalized * loss_per_lot
        estimated_percent = estimated / capital * 100.0
        if estimated > maximum_money + 1e-9:
            raise PositionSizingError("El volumen excede el riesgo máximo permitido.")

        return PositionSizingResult(
            allowed=True, mode=mode, volume=normalized,
            requested_risk=requested, estimated_risk_money=round(estimated, 2),
            estimated_risk_percent=round(estimated_percent, 6),
            stop_distance=distance, money_per_price_unit=money_per_unit,
            raw_volume=raw, normalized_volume=normalized,
            balance=balance, equity=equity,
            order_volumes=order_volumes,
            order_count=len(order_volumes),
            max_order_volume=volume_max,
        )


position_sizing_service = PositionSizingService()
