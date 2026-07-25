"""Fixed symbol catalogs supported by Kraken.

The catalogs are code-defined so the UI can show them before a broker terminal
is connected. Database migrations are explicit and are never triggered here.
"""

BRIDGE_CATALOG = "BRIDGE_SYNTHETICS"
WELTRADE_CATALOG = "WELTRADE_SYNTHETICS"


def _definition(
    canonical_name,
    display_name,
    mt5_symbol,
    catalog,
    broker,
    category,
    sort_order,
):
    return {
        "canonical_name": canonical_name,
        "display_name": display_name,
        "mt5_symbol": mt5_symbol,
        "catalog": catalog,
        "broker": broker,
        "category": category,
        "enabled": True,
        "sort_order": sort_order,
    }


BRIDGE_SYMBOLS = {
    **{
        f"EMASVOL{value}": _definition(
            f"EMASVOL{value}", f"EmasVol{value}", f"EmasVol{value}",
            BRIDGE_CATALOG, "BRIDGE MARKETS", "EMAS", index,
        )
        for index, value in enumerate(
            (10, 20, 30, 40, 50, 60, 70, 80, 90, 100), start=1
        )
    },
    **{
        f"LIONX{value}": _definition(
            f"LIONX{value}", f"LionX{value}", f"LionX{value}",
            BRIDGE_CATALOG, "BRIDGE MARKETS", "LION", index,
        )
        for index, value in enumerate(
            (25, 40, 50, 60, 75, 90, 100, 120, 150, 200), start=11
        )
    },
}


def _weltrade_group(prefix, display_prefix, values, category, start):
    return {
        f"{prefix}{value}": _definition(
            f"{prefix}{value}",
            f"{display_prefix} {value}",
            f"{display_prefix} {value}",
            WELTRADE_CATALOG,
            "WELTRADE",
            category,
            start + index,
        )
        for index, value in enumerate(values)
    }


WELTRADE_SYMBOLS = {
    **_weltrade_group("FXVOL", "FX Vol", (20, 40, 60, 80, 99), "FX_VOL", 1),
    **_weltrade_group("SFXVOL", "SFX Vol", (20, 40, 60, 80, 99), "SFX_VOL", 6),
    **_weltrade_group(
        "GAINX", "GainX", (400, 600, 800, 999, 1200), "GAINX", 11
    ),
    **_weltrade_group(
        "PAINX", "PainX", (400, 600, 800, 999, 1200), "PAINX", 16
    ),
    **_weltrade_group("FLIPX", "FlipX", (1, 2, 3, 4, 5), "FLIPX", 21),
}

SYNTHETIC_SYMBOLS = {**BRIDGE_SYMBOLS, **WELTRADE_SYMBOLS}


def get_symbols(catalog=None):
    return [
        name
        for name, config in SYNTHETIC_SYMBOLS.items()
        if catalog is None or config["catalog"] == catalog
    ]


def get_symbol(symbol):
    canonical = normalize_symbol(symbol)
    return SYNTHETIC_SYMBOLS.get(canonical) if canonical else None


def get_symbol_catalog(catalog=None):
    values = [
        dict(config)
        for config in SYNTHETIC_SYMBOLS.values()
        if catalog is None or config["catalog"] == catalog
    ]
    return sorted(
        values,
        key=lambda item: (item["catalog"], item["category"], item["sort_order"]),
    )


def symbol_exists(symbol):
    return get_symbol(symbol) is not None


def get_mt5_symbol(symbol):
    config = get_symbol(symbol)
    return config["mt5_symbol"] if config else None


def get_all_mt5_symbols(catalog=None):
    return [item["mt5_symbol"] for item in get_symbol_catalog(catalog)]


def normalize_symbol(symbol):
    if not isinstance(symbol, str):
        return None
    compact = "".join(symbol.strip().upper().split())
    return compact if compact in SYNTHETIC_SYMBOLS else None


def get_symbol_count(catalog=None):
    return len(get_symbols(catalog))
