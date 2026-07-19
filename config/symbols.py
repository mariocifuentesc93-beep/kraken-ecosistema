SYNTHETIC_SYMBOLS = {
    "EMASVOL10": {"mt5_symbol": "EmasVol10"},
    "EMASVOL20": {"mt5_symbol": "EmasVol20"},
    "EMASVOL30": {"mt5_symbol": "EmasVol30"},
    "EMASVOL40": {"mt5_symbol": "EmasVol40"},
    "EMASVOL50": {"mt5_symbol": "EmasVol50"},
    "EMASVOL60": {"mt5_symbol": "EmasVol60"},
    "EMASVOL70": {"mt5_symbol": "EmasVol70"},
    "EMASVOL80": {"mt5_symbol": "EmasVol80"},
    "EMASVOL90": {"mt5_symbol": "EmasVol90"},
    "EMASVOL100": {"mt5_symbol": "EmasVol100"},
    "LIONX25": {"mt5_symbol": "LionX25"},
    "LIONX40": {"mt5_symbol": "LionX40"},
    "LIONX50": {"mt5_symbol": "LionX50"},
    "LIONX60": {"mt5_symbol": "LionX60"},
    "LIONX75": {"mt5_symbol": "LionX75"},
    "LIONX90": {"mt5_symbol": "LionX90"},
    "LIONX100": {"mt5_symbol": "LionX100"},
    "LIONX120": {"mt5_symbol": "LionX120"},
    "LIONX150": {"mt5_symbol": "LionX150"},
    "LIONX200": {"mt5_symbol": "LionX200"},
}


# ==========================================================
# SYMBOLS
# ==========================================================

def get_symbols():

    return list(SYNTHETIC_SYMBOLS.keys())


def get_symbol(symbol):

    if not symbol:

        return None

    return SYNTHETIC_SYMBOLS.get(symbol.upper())


def symbol_exists(symbol):

    return get_symbol(symbol) is not None


def get_mt5_symbol(symbol):

    cfg = get_symbol(symbol)

    if cfg is None:

        return None

    return cfg["mt5_symbol"]


def get_all_mt5_symbols():

    return [

        cfg["mt5_symbol"]

        for cfg in SYNTHETIC_SYMBOLS.values()

    ]


def normalize_symbol(symbol):

    if not symbol:

        return None

    symbol = symbol.upper().replace(" ", "")

    return symbol if symbol in SYNTHETIC_SYMBOLS else None


def get_symbol_count():

    return len(SYNTHETIC_SYMBOLS)