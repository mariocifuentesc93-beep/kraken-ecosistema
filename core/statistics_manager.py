from datetime import datetime

from repositories.operation_repository import operation_repository
from repositories.profile_repository import profile_repository
from repositories.daily_statistics_repository import (
    daily_statistics_repository,
)
from repositories.symbol_statistics_repository import (
    symbol_statistics_repository,
)


class StatisticsManager:

    # =====================================================
    # ACTUALIZAR PERFIL
    # =====================================================

    def update_profile_statistics(self, profile_id):

        profile = profile_repository.get_by_id(profile_id)

        if profile is None:
            return

        operations = operation_repository.get_by_profile(profile_id)

        total = len(operations)

        wins = 0
        losses = 0
        breakeven = 0

        gross_profit = 0.0
        gross_loss = 0.0

        symbols = {}

        for operation in operations:

            profit = float(operation.profit)

            symbol = operation.symbol

            if symbol not in symbols:

                symbols[symbol] = {
                    "operations": 0,
                    "wins": 0,
                    "losses": 0,
                    "breakeven": 0,
                    "profit": 0.0,
                    "loss": 0.0,
                }

            stats = symbols[symbol]

            stats["operations"] += 1

            if profit > 0:

                wins += 1

                gross_profit += profit

                stats["wins"] += 1

                stats["profit"] += profit

            elif profit < 0:

                losses += 1

                gross_loss += profit

                stats["losses"] += 1

                stats["loss"] += profit

            else:

                breakeven += 1

                stats["breakeven"] += 1

        net_profit = gross_profit + gross_loss

        if total:

            win_rate = round(
                wins / total * 100,
                2,
            )

        else:

            win_rate = 0.0

        profile.update_statistics(
            total,
            wins,
            losses,
            breakeven,
            gross_profit,
            gross_loss,
        )

        profile_repository.update(profile)

        self.__update_daily(
            profile_id,
            total,
            wins,
            losses,
            breakeven,
            gross_profit,
            gross_loss,
            net_profit,
            win_rate,
        )

        self.__update_symbols(
            profile_id,
            symbols,
        )

    # =====================================================

    def __update_daily(
        self,
        profile_id,
        operations,
        wins,
        losses,
        breakeven,
        gross_profit,
        gross_loss,
        net_profit,
        win_rate,
    ):

        daily_statistics_repository.save(
            profile_id=profile_id,
            statistic_date=datetime.now().strftime("%Y-%m-%d"),
            operations=operations,
            wins=wins,
            losses=losses,
            breakeven=breakeven,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            net_profit=net_profit,
            win_rate=win_rate,
        )

    # =====================================================

    def __update_symbols(
        self,
        profile_id,
        symbols,
    ):

        for symbol, data in symbols.items():

            if data["operations"]:

                win_rate = round(
                    data["wins"] /
                    data["operations"] * 100,
                    2,
                )

            else:

                win_rate = 0.0

            symbol_statistics_repository.save(
                profile_id=profile_id,
                symbol=symbol,
                operations=data["operations"],
                wins=data["wins"],
                losses=data["losses"],
                breakeven=data["breakeven"],
                profit=data["profit"],
                loss=data["loss"],
                win_rate=win_rate,
            )

    # =====================================================

    def refresh_all(self):

        profiles = profile_repository.get_all()

        for profile in profiles:

            self.update_profile_statistics(
                profile.id
            )


statistics_manager = StatisticsManager()