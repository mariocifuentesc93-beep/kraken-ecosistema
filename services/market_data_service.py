"""Read-only market data for the simulation pipeline.

This service deliberately never submits MT5 trade requests.  It exposes a
uniform quote whether it is backed by an active MT5 terminal or the local,
deterministic simulation provider.
"""

from datetime import datetime, timezone

import MetaTrader5 as mt5

from config.symbols import (
    BRIDGE_CATALOG,
    get_mt5_symbol,
    get_symbols,
    symbol_exists,
)
from mt5.connector import mt5_connector


class MarketDataService:
    def __init__(self, freshness_seconds=15):
        self.freshness_seconds = freshness_seconds

    @staticmethod
    def _fallback_quote(symbol):
        # Stable values make an offline simulation repeatable without looking
        # like a live quote or making an MT5 call.
        base = 100.0 + (sum(map(ord, symbol.upper())) % 500) / 10
        spread = 0.10
        now = datetime.now(timezone.utc)
        return {
            "symbol": symbol.upper(), "bid": round(base, 5),
            "ask": round(base + spread, 5), "last": round(base + spread / 2, 5),
            "spread": spread, "timestamp": now, "source": "FALLBACK",
            "available": True, "market_open": True, "fresh": True,
            "stale_reason": "", "metadata": {},
        }

    def quote(self, symbol, freshness_seconds=None, allow_fallback=True):
        symbol = (symbol or "").upper()
        if not symbol_exists(symbol):
            return {
                "symbol": symbol, "bid": None, "ask": None, "last": None,
                "spread": None, "timestamp": None, "source": "NONE",
                "available": False, "market_open": False, "fresh": False,
                "stale_reason": "SÃ­mbolo no configurado.", "metadata": {},
            }

        if not mt5_connector.is_connected():
            return self._fallback_quote(symbol) if allow_fallback else self._unavailable(symbol, "MT5 no conectado.")

        mt5_symbol = get_mt5_symbol(symbol)
        info = mt5.symbol_info(mt5_symbol)
        if info is None:
            return self._fallback_quote(symbol) if allow_fallback else self._unavailable(symbol, "SÃ­mbolo no existe en MT5.")
        selected = bool(getattr(info, "visible", False) or mt5.symbol_select(mt5_symbol, True))
        if not selected:
            return self._fallback_quote(symbol) if allow_fallback else self._unavailable(symbol, "No se pudo seleccionar el sÃ­mbolo MT5.")
        tick = mt5.symbol_info_tick(mt5_symbol)
        if tick is None:
            return self._fallback_quote(symbol) if allow_fallback else self._unavailable(symbol, "MT5 no devolviÃ³ tick.")

        timestamp = datetime.fromtimestamp(getattr(tick, "time", 0), timezone.utc)
        age = (datetime.now(timezone.utc) - timestamp).total_seconds()
        threshold = self.freshness_seconds if freshness_seconds is None else freshness_seconds
        bid, ask = float(tick.bid), float(tick.ask)
        last = float(getattr(tick, "last", 0) or ((bid + ask) / 2))
        market_open = bool(getattr(info, "trade_mode", 1))
        return {
            "symbol": symbol, "bid": bid, "ask": ask, "last": last,
            "spread": round(ask - bid, 10), "timestamp": timestamp,
            "source": "MT5", "available": True, "market_open": market_open,
            "fresh": age <= threshold,
            "stale_reason": "Tick MT5 vencido." if age > threshold else "",
            "metadata": {"mt5_symbol": mt5_symbol, "digits": getattr(info, "digits", 0)},
        }

    @staticmethod
    def _unavailable(symbol, reason):
        return {"symbol": symbol, "bid": None, "ask": None, "last": None,
                "spread": None, "timestamp": None, "source": "NONE",
                "available": False, "market_open": False, "fresh": False,
                "stale_reason": reason, "metadata": {}}

    def validate_configured_symbols(self):
        """Validate all configured symbols against MT5; never enables trading."""
        connected = mt5_connector.is_connected()
        results = []
        for symbol in get_symbols(BRIDGE_CATALOG):
            mt5_symbol = get_mt5_symbol(symbol)
            info = mt5.symbol_info(mt5_symbol) if connected else None
            exists = info is not None
            selected = bool(exists and (getattr(info, "visible", False) or mt5.symbol_select(mt5_symbol, True)))
            tick = mt5.symbol_info_tick(mt5_symbol) if selected else None
            results.append({
                "symbol": symbol, "mt5_symbol": mt5_symbol, "mt5_connected": connected,
                "exists": exists, "selected": selected, "tick_available": tick is not None,
                "metadata_available": info is not None,
            })
        return results


market_data_service = MarketDataService()
