"""Single pre-flight gate used before MT5 execution."""

from dataclasses import dataclass, field
import re


ACCOUNT_DISCONNECTED = "ACCOUNT_DISCONNECTED"
ACCOUNT_MISMATCH = "ACCOUNT_MISMATCH"
BROKER_MISMATCH = "BROKER_MISMATCH"
SYMBOL_NOT_FOUND = "SYMBOL_NOT_FOUND"
SYMBOL_DISABLED = "SYMBOL_DISABLED"
MARKET_CLOSED = "MARKET_CLOSED"
INSUFFICIENT_MARGIN = "INSUFFICIENT_MARGIN"
RISK_REJECTED = "RISK_REJECTED"
INVALID_VOLUME = "INVALID_VOLUME"
INVALID_SL = "INVALID_SL"
INVALID_TP = "INVALID_TP"
PROFILE_DISABLED = "PROFILE_DISABLED"
EXECUTION_MODE_OFF = "EXECUTION_MODE_OFF"


@dataclass(frozen=True)
class PreflightResult:
    allowed: bool
    state: str
    code: str = ""
    reason: str = ""
    details: dict = field(default_factory=dict)


class ExecutionPreflightService:
    ALLOWED_MODES = {"SIMULATION", "PAPER", "DEMO", "LIVE"}

    def __init__(self, mt5_adapter=None, terminal_provider=None):
        self._adapter_was_injected = mt5_adapter is not None
        self._adapter = mt5_adapter
        self._terminal_provider = terminal_provider

    def _mt5(self):
        if self._adapter is None:
            import MetaTrader5 as mt5
            self._adapter = mt5
        return self._adapter

    def _terminal(self, account):
        if self._terminal_provider is not None:
            return self._terminal_provider(
                getattr(account, "mt5_terminal_id", None)
            )
        from repositories.mt5_terminal_repository import mt5_terminal_repository
        terminal_id = getattr(account, "mt5_terminal_id", None)
        return mt5_terminal_repository.get_by_id(terminal_id) if terminal_id else None

    @staticmethod
    def _reject(code, reason, details=None):
        return PreflightResult(False, "BLOCKED", code, reason, details or {})

    @staticmethod
    def _normalized(value):
        return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())

    @staticmethod
    def _field(source, name, default=None):
        if isinstance(source, dict):
            return source.get(name, default)
        return getattr(source, name, default)

    def _operational_symbol(self, symbol):
        if self._adapter_was_injected:
            return symbol
        from core.config_service import get_symbol

        configured = get_symbol(symbol)
        return getattr(configured, "mt5_symbol", None) or symbol

    def validate(self, signal, profile, account, volume, risk_result=None):
        mode = str(getattr(profile, "execution_mode", "OFF") or "OFF").upper()
        details = {
            "signal_id": getattr(signal, "id", None),
            "profile_id": getattr(profile, "id", None),
            "account_id": getattr(account, "id", None),
            "terminal_id": getattr(account, "mt5_terminal_id", None),
            "symbol": getattr(signal, "symbol", ""),
            "volume": float(volume or 0),
            "risk": risk_result or {},
            "execution_mode": mode,
        }
        if not getattr(profile, "active", True) or not getattr(profile, "enabled", True):
            return self._reject(PROFILE_DISABLED, "El perfil está deshabilitado.", details)
        if mode == "OFF" or mode not in self.ALLOWED_MODES:
            return self._reject(EXECUTION_MODE_OFF, f"Modo de ejecución no permitido: {mode}.", details)
        if not risk_result or not risk_result.get("allowed", False):
            return self._reject(
                RISK_REJECTED,
                (risk_result or {}).get("reason", "El riesgo no fue aprobado."),
                details,
            )
        if float(volume or 0) <= 0:
            return self._reject(INVALID_VOLUME, "El volumen debe ser mayor que cero.", details)
        entry = float(getattr(signal, "entry", 0) or 0)
        sl = float(getattr(signal, "stop_loss", 0) or 0)
        targets = list(getattr(signal, "take_profits", []) or [])
        if entry <= 0 or sl <= 0 or entry == sl:
            return self._reject(INVALID_SL, "Entrada o Stop Loss inválidos.", details)
        side = str(getattr(signal, "direction", "")).upper()
        if side not in {"BUY", "SELL"}:
            return self._reject(INVALID_SL, "Dirección de operación inválida.", details)
        if (side == "BUY" and sl >= entry) or (side == "SELL" and sl <= entry):
            return self._reject(INVALID_SL, "Stop Loss incompatible con la dirección.", details)
        if not targets or float(targets[0] or 0) <= 0:
            return self._reject(INVALID_TP, "La señal no contiene Take Profit válido.", details)
        tp = float(targets[0])
        if (side == "BUY" and tp <= entry) or (side == "SELL" and tp >= entry):
            return self._reject(INVALID_TP, "Take Profit incompatible con la dirección.", details)

        # SIMULATION never requires or changes a real terminal connection.
        if mode in {"SIMULATION", "PAPER"}:
            return PreflightResult(True, "READY", details=details)

        terminal = self._terminal(account)
        mt5 = self._mt5()
        terminal_info = mt5.terminal_info()
        if terminal is None or terminal_info is None:
            return self._reject(ACCOUNT_DISCONNECTED, "Terminal MT5 no disponible.", details)
        account_info = mt5.account_info()
        if account_info is None or not bool(getattr(terminal_info, "connected", True)):
            return self._reject(ACCOUNT_DISCONNECTED, "Cuenta MT5 desconectada.", details)
        expected_login = int(getattr(account, "login", 0) or 0)
        detected_login = int(getattr(account_info, "login", 0) or 0)
        details.update(expected_login=expected_login, detected_login=detected_login)
        if expected_login != detected_login:
            return self._reject(ACCOUNT_MISMATCH, "El login conectado no coincide con la cuenta destino.", details)
        expected_broker = self._normalized(getattr(terminal, "broker", ""))
        detected_broker = self._normalized(
            getattr(account_info, "company", "") or getattr(account_info, "server", "")
        )
        if expected_broker and expected_broker not in detected_broker and detected_broker not in expected_broker:
            return self._reject(BROKER_MISMATCH, "El broker conectado no coincide con la terminal configurada.", details)
        symbol = self._operational_symbol(
            str(getattr(signal, "symbol", ""))
        )
        details["operational_symbol"] = symbol
        info = mt5.symbol_info(symbol)
        if info is None:
            return self._reject(SYMBOL_NOT_FOUND, f"El símbolo {symbol} no existe.", details)
        if not bool(getattr(info, "visible", False)):
            if not mt5.symbol_select(symbol, True):
                return self._reject(SYMBOL_DISABLED, f"No se pudo habilitar {symbol}.", details)
            info = mt5.symbol_info(symbol)
        if info is None or not bool(getattr(info, "visible", False)):
            return self._reject(SYMBOL_DISABLED, f"El símbolo {symbol} no está visible.", details)
        if not bool(getattr(terminal_info, "trade_allowed", False)) or not bool(
            getattr(account_info, "trade_allowed", False)
        ):
            return self._reject(ACCOUNT_DISCONNECTED, "Trading no permitido en terminal o cuenta.", details)
        trade_mode = int(getattr(info, "trade_mode", 0) or 0)
        if (
            trade_mode in {0, 1}
            or (side == "BUY" and trade_mode == 3)
            or (side == "SELL" and trade_mode == 2)
        ):
            return self._reject(MARKET_CLOSED, "El mercado está cerrado para el símbolo.", details)

        minimum = float(getattr(info, "volume_min", 0) or 0)
        maximum = float(getattr(info, "volume_max", 0) or 0)
        step = float(getattr(info, "volume_step", 0) or 0)
        if minimum <= 0 or maximum < minimum or step <= 0 or not (
            minimum <= float(volume) <= maximum
        ):
            return self._reject(INVALID_VOLUME, "Volumen fuera de límites MT5.", details)
        units = round(float(volume) / step)
        if abs(units * step - float(volume)) > 1e-9:
            return self._reject(INVALID_VOLUME, "Volumen incompatible con volume_step.", details)
        point = float(getattr(info, "point", 0) or 0)
        stops = float(getattr(info, "trade_stops_level", 0) or 0) * point
        freeze = float(getattr(info, "trade_freeze_level", 0) or 0) * point
        required = max(stops, freeze)
        if abs(entry - sl) < required:
            return self._reject(INVALID_SL, "Stop Loss incumple stops_level/freeze_level.", details)
        if abs(tp - entry) < required:
            return self._reject(INVALID_TP, "Take Profit incumple stops_level/freeze_level.", details)
        tick = mt5.symbol_info_tick(symbol)
        if tick is None or max(float(getattr(tick, "ask", 0) or 0), float(getattr(tick, "bid", 0) or 0)) <= 0:
            return self._reject(MARKET_CLOSED, "No existe precio negociable.", details)
        price = float(tick.ask if side == "BUY" else tick.bid)
        order_type = getattr(mt5, "ORDER_TYPE_BUY", 0) if side == "BUY" else getattr(mt5, "ORDER_TYPE_SELL", 1)
        margin = mt5.order_calc_margin(order_type, symbol, float(volume), price)
        free_margin = float(getattr(account_info, "margin_free", 0) or 0)
        balance = float(getattr(account_info, "balance", 0) or 0)
        equity = float(getattr(account_info, "equity", 0) or 0)
        details.update(balance=balance, equity=equity, free_margin=free_margin, required_margin=margin)
        if balance <= 0 or equity <= 0:
            return self._reject(ACCOUNT_DISCONNECTED, "Balance/equity de cuenta inválidos.", details)
        if margin is None or float(margin) > free_margin:
            return self._reject(INSUFFICIENT_MARGIN, "Margen insuficiente.", details)
        return PreflightResult(True, "READY", details=details)


execution_preflight_service = ExecutionPreflightService()
