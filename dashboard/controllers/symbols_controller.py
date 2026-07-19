from services.symbol_service import symbol_service


class SymbolController:

    # ---------------------------------------------------------

    def get_all(self, profile_id):

        return symbol_service.get_all(profile_id)

    # ---------------------------------------------------------

    def create(
        self,
        profile_id,
        enabled=True,
        symbol="",
        description="",
        aliases="",
        risk=1.0,
        min_lot=0.01,
        max_lot=100.0,
        action="trade",
    ):

        return symbol_service.create(
            profile_id=profile_id,
            enabled=enabled,
            symbol=symbol,
            description=description,
            aliases=aliases,
            risk=risk,
            min_lot=min_lot,
            max_lot=max_lot,
            action=action,
        )

    # ---------------------------------------------------------

    def delete(self, symbol_id):

        symbol_service.delete(symbol_id)


symbol_controller = SymbolController()