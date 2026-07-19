from config.symbols import symbol_exists
from core.config_service import is_symbol_enabled


def validate_signal(signal):

    errors = []

    # ---------------------------------------------------------

    if signal is None:

        return False, ["Señal vacía"]

    # ---------------------------------------------------------
    # Símbolo
    # ---------------------------------------------------------

    if not signal.symbol:

        errors.append("Símbolo no detectado")

    elif not symbol_exists(signal.symbol):

        errors.append(

            f"Símbolo no soportado: {signal.symbol}"

        )

    elif not is_symbol_enabled(signal.symbol):

        errors.append(

            f"Símbolo deshabilitado: {signal.symbol}"

        )

    # ---------------------------------------------------------
    # Dirección
    # ---------------------------------------------------------

    if signal.direction not in ("BUY", "SELL"):

        errors.append("Dirección inválida")

    # ---------------------------------------------------------
    # Entrada
    # ---------------------------------------------------------

    entry_type = signal.metadata.get(

        "entry_type",

        "MARKET",

    )

    if entry_type not in (

        "MARKET",

        "LIMIT",

        "STOP",

    ):

        errors.append("Tipo de entrada inválido")

    # ---------------------------------------------------------
    # Precio
    # ---------------------------------------------------------

    if signal.entry <= 0:

        errors.append("Precio de entrada inválido")

    # ---------------------------------------------------------
    # Stop Loss
    # ---------------------------------------------------------

    if signal.stop_loss <= 0:

        errors.append("Stop Loss inválido")

    # ---------------------------------------------------------
    # Take Profit
    # ---------------------------------------------------------

    if not signal.take_profits:

        errors.append("Debe existir al menos un Take Profit")

    # ---------------------------------------------------------

    return len(errors) == 0, errors