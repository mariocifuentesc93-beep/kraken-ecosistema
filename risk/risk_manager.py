from risk.money_management import money_management
from risk.position_sizing import position_sizing
from risk.daily_limits import daily_limits
from risk.drawdown_manager import drawdown_manager
from risk.exposure_manager import exposure_manager
from risk.break_even import break_even
from risk.trailing_stop import trailing_stop
from risk.partial_tp import partial_tp
from risk.risk_rules import risk_rules
from repositories.daily_statistics_repository import daily_statistics_repository


class RiskManager:

    def __init__(self):

        self.money_management = money_management
        self.position_sizing = position_sizing
        self.daily_limits = daily_limits
        self.drawdown_manager = drawdown_manager
        self.exposure_manager = exposure_manager
        self.break_even = break_even
        self.trailing_stop = trailing_stop
        self.partial_tp = partial_tp
        self.risk_rules = risk_rules

    # ---------------------------------------------------------

    def validate(
        self,
        signal,
        account=None,
        profile=None,
    ):

        print()
        print("-" * 60)
        print("🛡️ RISK MANAGER")
        print("-" * 60)

        if profile is not None:
            self.money_management.load_profile(profile)

            if account is not None and getattr(account, "balance", 0) > 0:
                self.drawdown_manager.update(
                    float(account.balance),
                    float(getattr(account, "equity", account.balance)),
                )
            profile_drawdown_limit = float(
                getattr(profile, "max_drawdown", 0.0) or 0.0
            )
            if (
                profile_drawdown_limit
                and self.drawdown_manager.current_drawdown >= profile_drawdown_limit
            ):
                return False, "Drawdown máximo alcanzado para el perfil."

            daily_loss_limit = float(
                getattr(profile, "max_daily_loss", 0.0) or 0.0
            )
            daily_profit_limit = float(
                getattr(profile, "max_daily_profit", 0.0) or 0.0
            )
            if daily_loss_limit or daily_profit_limit:
                statistics = daily_statistics_repository.today(profile.id)
                daily_profit = float(
                    statistics["net_profit"] if statistics else 0.0
                )
                if daily_loss_limit and daily_profit <= -daily_loss_limit:
                    return False, "Límite diario de pérdidas alcanzado para el perfil."
                if daily_profit_limit and daily_profit >= daily_profit_limit:
                    return False, "Límite diario de ganancias alcanzado para el perfil."

        # -----------------------------------------------------
        # Drawdown
        # -----------------------------------------------------

        if getattr(self.drawdown_manager, "enabled", False):

            if self.drawdown_manager.exceeded():

                return False, "Drawdown máximo alcanzado."

        # -----------------------------------------------------
        # Límites diarios
        # -----------------------------------------------------

        if getattr(self.daily_limits, "enabled", False):

            if hasattr(self.daily_limits, "validate"):

                ok, msg = self.daily_limits.validate()

                if not ok:
                    return False, msg

        # -----------------------------------------------------
        # Exposición
        # -----------------------------------------------------

        if getattr(self.exposure_manager, "enabled", False):

            if hasattr(self.exposure_manager, "validate"):

                ok, msg = self.exposure_manager.validate(signal)

                if not ok:
                    return False, msg

        # -----------------------------------------------------
        # Reglas
        # -----------------------------------------------------

        if getattr(self.risk_rules, "enabled", False):

            if hasattr(self.risk_rules, "validate"):

                ok, msg = self.risk_rules.validate(signal)

                if not ok:
                    return False, msg

        return True, "Riesgo aprobado."

    # ---------------------------------------------------------

    def calculate_lot(
        self,
        signal,
        profile=None,
        account=None,
    ):

        if profile is not None:
            self.money_management.load_profile(profile)

        mode = str(self.money_management.mode).upper()

        if mode == "FIXED":

            lot = self.money_management.fixed_lot

        elif mode == "AMOUNT":

            lot = self.position_sizing.calculate_by_amount(
                symbol=signal.symbol,
                risk_amount=self.money_management.risk_amount,
                entry_price=signal.entry,
                stop_loss=signal.stop_loss,
            )

        else:

            lot = self.position_sizing.calculate_by_percent(
                symbol=signal.symbol,
                risk_percent=self.money_management.risk_percent,
                entry_price=signal.entry,
                stop_loss=signal.stop_loss,
            )

        lot = self.money_management.validate_lot(lot)

        signal.volume = lot

        print(f"[RiskManager] Lote calculado: {lot}")

        return lot

    # ---------------------------------------------------------

    def manage_open_operation(
        self,
        operation,
    ):

        try:
            self.partial_tp.check(operation)
        except Exception:
            pass

        try:
            self.break_even.check(operation)
        except Exception:
            pass

        try:
            self.trailing_stop.check(operation)
        except Exception:
            pass

    # ---------------------------------------------------------

    def get_summary(self):

        return {

            "money_management": self.money_management.get_summary(),

            "daily_limits": self.daily_limits.get_summary(),

            "drawdown": self.drawdown_manager.get_summary(),

            "exposure": self.exposure_manager.get_summary(),

            "break_even": self.break_even.get_summary(),

            "trailing": self.trailing_stop.get_summary(),

            "partial_tp": self.partial_tp.get_summary(),

            "rules": self.risk_rules.get_summary(),

        }


risk_manager = RiskManager()
