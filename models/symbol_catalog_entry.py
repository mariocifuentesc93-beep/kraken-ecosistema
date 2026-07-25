from dataclasses import dataclass


@dataclass(frozen=True)
class SymbolCatalogEntry:
    canonical_name: str
    display_name: str
    mt5_symbol: str
    catalog: str
    broker: str
    category: str
    enabled: bool = True
    sort_order: int = 0
    availability: str = "NOT_VERIFIED"
