from repositories.symbol_repository import symbol_repository


class SymbolService:

    # ---------------------------------------------------------

    def get_all(self, profile_id):

        return symbol_repository.get_all(profile_id)

    # ---------------------------------------------------------

    def create(
        self,
        profile_id,
        enabled,
        symbol,
        description="",
        aliases="",
        risk=1.0,
        min_lot=0.01,
        max_lot=100.0,
        action="trade",
        mt5_symbol=None,
    ):

        return symbol_repository.create(
            profile_id=profile_id,
            enabled=enabled,
            symbol=symbol,
            mt5_symbol=mt5_symbol or symbol,
            description=description,
            aliases=aliases,
            risk=risk,
            min_lot=min_lot,
            max_lot=max_lot,
            action=action,
        )

    # ---------------------------------------------------------

    def delete(self, symbol_id):

        symbol_repository.delete(symbol_id)


symbol_service = SymbolService()
