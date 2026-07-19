from datetime import datetime, timedelta

from config.symbols import symbol_exists
from core.config_service import is_symbol_enabled


def validate_signal(signal, now=None):
    errors = []
    if signal is None:
        return False, ["Señal vacía"]

    now = now or datetime.now()
    if getattr(signal, "received_at", now) < now - timedelta(minutes=5):
        errors.append("Señal expirada")

    if not signal.symbol:
        errors.append("Símbolo no detectado")
    elif not symbol_exists(signal.symbol):
        errors.append(f"Símbolo no soportado: {signal.symbol}")
    elif not is_symbol_enabled(signal.symbol):
        errors.append(f"Símbolo deshabilitado: {signal.symbol}")

    if signal.direction not in ("BUY", "SELL"):
        errors.append("Dirección inválida")
    if signal.metadata.get("entry_type", "MARKET") not in ("MARKET", "LIMIT", "STOP"):
        errors.append("Tipo de entrada inválido")
    if signal.entry <= 0:
        errors.append("Precio de entrada inválido")
    if signal.stop_loss <= 0:
        errors.append("Stop Loss inválido")
    elif signal.direction == "BUY" and signal.stop_loss >= signal.entry:
        errors.append("Stop Loss debe estar por debajo de la entrada BUY")
    elif signal.direction == "SELL" and signal.stop_loss <= signal.entry:
        errors.append("Stop Loss debe estar por encima de la entrada SELL")
    if not signal.take_profits:
        errors.append("Debe existir al menos un Take Profit")
    return not errors, errors
