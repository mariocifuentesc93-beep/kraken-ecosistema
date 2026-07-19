import MetaTrader5 as mt5

from core.config_service import get_symbol


# ==========================================================
# INTERNO
# ==========================================================

def _mt5_symbol(symbol):

    item = get_symbol(symbol)

    if item is None:
        return None

    return item.mt5_symbol


# ==========================================================
# FUNCIONES
# ==========================================================

def symbol_exists(symbol):

    mt5_symbol = _mt5_symbol(symbol)

    if mt5_symbol is None:
        return False

    return mt5.symbol_info(mt5_symbol) is not None


def select_symbol(symbol):

    mt5_symbol = _mt5_symbol(symbol)

    if mt5_symbol is None:
        return False

    return mt5.symbol_select(mt5_symbol, True)


def get_symbol_info(symbol):

    mt5_symbol = _mt5_symbol(symbol)

    if mt5_symbol is None:
        return None

    return mt5.symbol_info(mt5_symbol)


def get_tick(symbol):

    mt5_symbol = _mt5_symbol(symbol)

    if mt5_symbol is None:
        return None

    return mt5.symbol_info_tick(mt5_symbol)


def get_bid(symbol):

    tick = get_tick(symbol)

    if tick is None:
        return None

    return tick.bid


def get_ask(symbol):

    tick = get_tick(symbol)

    if tick is None:
        return None

    return tick.ask


def get_spread(symbol):

    tick = get_tick(symbol)

    if tick is None:
        return None

    return tick.ask - tick.bid