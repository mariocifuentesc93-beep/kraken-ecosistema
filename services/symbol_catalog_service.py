"""Broker-independent availability checks for the fixed symbol catalog."""

from config.symbols import get_symbol

NOT_VERIFIED = "NOT_VERIFIED"
AVAILABLE = "AVAILABLE"
UNAVAILABLE = "UNAVAILABLE"


class SymbolCatalogService:
    def definition(self, symbol):
        return get_symbol(symbol)

    def availability(self, symbol, terminal=None):
        definition = get_symbol(symbol)
        if definition is None:
            return UNAVAILABLE
        if terminal is None:
            return NOT_VERIFIED
        return AVAILABLE if terminal.symbol_info(definition["mt5_symbol"]) else UNAVAILABLE

    def require_available(self, symbol, terminal=None):
        status = self.availability(symbol, terminal)
        if status == UNAVAILABLE:
            definition = get_symbol(symbol)
            mt5_name = definition["mt5_symbol"] if definition else symbol
            raise ValueError(
                f"El símbolo {mt5_name} no está disponible en la terminal MT5."
            )
        return status


symbol_catalog_service = SymbolCatalogService()
