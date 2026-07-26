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

    def __init__(self, sizing_service=None, symbol_info_provider=None):

        self.money_management = money_management
        self.position_sizing = position_sizing
        self.daily_limits = daily_limits
        self.drawdown_manager = drawdown_manager
        self.exposure_manager = exposure_manager
        self.break_even = break_even
        self.trailing_stop = trailing_stop
        self.partial_tp = partial_tp
        self.risk_rules = risk_rules
        self._sizing_service = sizing_service
        self._symbol_info_provider = symbol_info_provider

    def _get_sizing_service(self):
        if self._sizing_service is None:
            from risk.position_sizing_service import position_sizing_service
            self._sizing_service = position_sizing_service
        return self._sizing_service

    def _get_symbol_info(self, account, symbol):
        if self._symbol_info_provider is not None:
            return self._symbol_info_provider(account, symbol)
        from mt5.connector import mt5_connector
        expected = int(getattr(account, "login", 0) or 0)
        detected = int(getattr(mt5_connector, "current_account", 0) or 0)
        if not expected or detected != expected:
            raise ValueError(
                "La cuenta MT5 conectada no coincide con la cuenta destino del perfil."
            )
        info = mt5_connector.get_symbol_info(symbol)
        if info is None:
            raise ValueError(f"No existe información MT5 para {symbol}.")
        return info

    def _calculate_profile_sizing(self, signal, profile, account):
        result = self._get_sizing_service().calculate(
            profile=profile,
            account=account,
            symbol=signal.symbol,
            direction=signal.direction,
            entry=signal.entry,
            stop_loss=signal.stop_loss,
            symbol_info=self._get_symbol_info(account, signal.symbol),
        )
        details = result.to_dict()
        details["profile_id"] = getattr(profile, "id", None)
        details["mt5_account_id"] = getattr(account, "id", None)
        details["symbol"] = signal.symbol
        details["stop_loss"] = signal.stop_loss
        signal.metadata["position_sizing"] = details
        signal.volume = result.volume
        return result

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

        if profile is not None and account is not None:
            try:
                self._calculate_profile_sizing(signal, profile, account)
            except Exception as error:
                signal.metadata["position_sizing"] = {
                    "allowed": False,
                    "reason": str(error),
                    "profile_id": getattr(profile, "id", None),
                    "mt5_account_id": getattr(account, "id", None),
                }
                return False, str(error)

        return True, "Riesgo aprobado."

    # ---------------------------------------------------------

    def calculate_lot(
        self,
        signal,
        profile=None,
        account=None,
    ):

        cached = signal.metadata.get("position_sizing", {})
        if cached.get("allowed"):
            return float(cached["volume"])
        result = self._calculate_profile_sizing(signal, profile, account)
        return result.volume

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
