from config.symbols import symbol_exists


def _enabled_for_profile(signal, profile, enabled_symbols=None):

    if enabled_symbols is None and profile is not None:

        from repositories.symbol_repository import symbol_repository

        enabled_symbols = symbol_repository.get_enabled(profile.id)

    if enabled_symbols is not None:

        signal_symbol = signal.symbol.upper()

        return any(
            str(getattr(item, "symbol", item)).upper() == signal_symbol
            for item in enabled_symbols
        )

    from core.config_service import is_symbol_enabled

    return is_symbol_enabled(signal.symbol)


def validate_signal(
    signal,
    profile=None,
    enabled_symbols=None,
):
    """
    Valida una señal para el perfil que realmente va a procesarla.

    ``enabled_symbols`` es un punto de inyección para pruebas y evita acceder a
    la configuración global o a SQLite.
    """

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

    elif not _enabled_for_profile(
        signal,
        profile,
        enabled_symbols,
    ):

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
