"""Account-scoped symbol resolution prepared for multiple MT5 terminals."""

from dataclasses import dataclass

from config.symbols import get_symbol

NOT_VERIFIED = "NOT_VERIFIED"
AVAILABLE = "AVAILABLE"
UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class ResolvedSymbol:
    canonical_name: str
    mt5_symbol: str
    mt5_account_id: int
    profile_id: int
    catalog_id: str
    availability: str


class SymbolCatalogService:
    """Resolve symbols without owning a terminal or global connection.

    ``connection_registry`` is an optional future-facing collaborator exposing
    ``get(mt5_account_id)``. Its returned terminal instance may expose
    ``symbol_info(name)``. No terminal is created or connected here.
    """

    def definition(self, symbol, catalog_id=None):
        definition = get_symbol(symbol)
        if definition is None:
            return None
        if catalog_id is not None and definition["catalog"] != catalog_id:
            return None
        return definition

    def resolve_symbol(
        self,
        canonical_symbol,
        mt5_account_id,
        catalog_id,
        profile_id=None,
        connection_registry=None,
    ):
        if mt5_account_id is None:
            raise ValueError("mt5_account_id es obligatorio para resolver el símbolo.")
        if profile_id is None:
            raise ValueError("profile_id es obligatorio para resolver el símbolo.")
        if not catalog_id:
            raise ValueError("catalog_id es obligatorio para resolver el símbolo.")

        definition = self.definition(canonical_symbol, catalog_id)
        if definition is None:
            raise ValueError(
                f"El símbolo {canonical_symbol} no pertenece al catálogo {catalog_id}."
            )

        status = NOT_VERIFIED
        if connection_registry is not None:
            terminal = connection_registry.get(mt5_account_id)
            if terminal is not None:
                status = (
                    AVAILABLE
                    if terminal.symbol_info(definition["mt5_symbol"])
                    else UNAVAILABLE
                )

        return ResolvedSymbol(
            canonical_name=definition["canonical_name"],
            mt5_symbol=definition["mt5_symbol"],
            mt5_account_id=mt5_account_id,
            profile_id=profile_id,
            catalog_id=catalog_id,
            availability=status,
        )

    def require_available(self, *args, **kwargs):
        resolved = self.resolve_symbol(*args, **kwargs)
        if resolved.availability == UNAVAILABLE:
            raise ValueError(
                f"El símbolo {resolved.mt5_symbol} no está disponible en la "
                f"cuenta MT5 {resolved.mt5_account_id}."
            )
        return resolved


symbol_catalog_service = SymbolCatalogService()
