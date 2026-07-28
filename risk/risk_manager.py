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

    def __init__(
        self,
        sizing_service=None,
        symbol_info_provider=None,
        connection_registry=None,
    ):

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
        self._connection_registry = connection_registry

    def _get_sizing_service(self):
        if self._sizing_service is None:
            from risk.position_sizing_service import position_sizing_service
            self._sizing_service = position_sizing_service
        return self._sizing_service

    def _connection_for(self, account):
        if self._connection_registry is None:
            from services.mt5_connection_registry import (
                mt5_connection_registry,
            )

            self._connection_registry = mt5_connection_registry
        return self._connection_registry.connection_for(
            account.id,
            getattr(account, "mt5_terminal_id", None),
        )

    def _get_symbol_info(self, account, symbol, profile=None):
        if self._symbol_info_provider is not None:
            return self._symbol_info_provider(account, symbol)
        from config.symbols import get_mt5_symbol
        if getattr(account, "mt5_terminal_id", None) is None:
            # Compatibility for legacy databases/tests. New operational
            # accounts are required to use the isolated terminal registry.
            from mt5.connector import mt5_connector

            expected = int(getattr(account, "login", 0) or 0)
            detected = int(
                getattr(mt5_connector, "current_account", 0) or 0
            )
            if not expected or detected != expected:
                raise ValueError(
                    "La cuenta MT5 conectada no coincide con la cuenta "
                    "destino del perfil."
                )
            operational_symbol = get_mt5_symbol(symbol) or symbol
            info = mt5_connector.get_symbol_info(operational_symbol)
            if info is None:
                raise ValueError(
                    f"No existe información MT5 para {symbol}."
                )
            return info
        connection = self._connection_for(account)
        info = connection.account_info()
        expected = int(getattr(account, "login", 0) or 0)
        detected = int(getattr(info, "login", 0) or 0)
        if not expected or detected != expected:
            raise ValueError(
                "La cuenta MT5 conectada no coincide con la cuenta destino del perfil."
            )
        from services.symbol_catalog_service import symbol_catalog_service

        operational_symbol = symbol_catalog_service.resolve_symbol(
            canonical_symbol=symbol,
            mt5_account_id=account.id,
            catalog_id=(
                getattr(profile, "catalog_id", None)
                or "BRIDGE_SYNTHETICS"
            ),
            profile_id=getattr(profile, "id", None),
        ).mt5_symbol
        symbol_info = connection.symbol_info(operational_symbol)
        if symbol_info is None:
            raise ValueError(f"No existe información MT5 para {symbol}.")
        if not bool(getattr(symbol_info, "visible", False)):
            connection.symbol_select(operational_symbol, True)
            symbol_info = connection.symbol_info(operational_symbol)
        return symbol_info

    def _refresh_destination_metrics(self, account):
        if self._symbol_info_provider is not None:
            return
        if getattr(account, "mt5_terminal_id", None) is None:
            from mt5.connector import mt5_connector

            info = mt5_connector.get_account_info()
        else:
            info = self._connection_for(account).account_info()
        expected = int(getattr(account, "login", 0) or 0)
        detected = int(getattr(info, "login", 0) or 0)
        if info is None or not expected or detected != expected:
            return
        account.balance = float(getattr(info, "balance", 0.0) or 0.0)
        account.equity = float(getattr(info, "equity", 0.0) or 0.0)
        account.free_margin = float(
            getattr(info, "margin_free", 0.0) or 0.0
        )
        account.connected = True

    def _execution_risk_context(self, signal, profile, account):
        """Return destination-specific executable price and MT5 loss per lot."""
        symbol_info = self._get_symbol_info(
            account, signal.symbol, profile
        )
        # Injected providers keep pure/unit tests independent from MT5.
        if self._symbol_info_provider is not None:
            return symbol_info, float(signal.entry), None

        side = str(signal.direction).strip().upper()

        if getattr(account, "mt5_terminal_id", None) is None:
            from config.symbols import get_mt5_symbol
            from mt5.connector import mt5_connector
            import MetaTrader5 as mt5

            operational_symbol = get_mt5_symbol(signal.symbol) or signal.symbol
            tick = mt5_connector.get_tick(operational_symbol)
            api = mt5
        else:
            from services.symbol_catalog_service import symbol_catalog_service

            operational_symbol = symbol_catalog_service.resolve_symbol(
                canonical_symbol=signal.symbol,
                mt5_account_id=account.id,
                catalog_id=(
                    getattr(profile, "catalog_id", None)
                    or "BRIDGE_SYNTHETICS"
                ),
                profile_id=getattr(profile, "id", None),
            ).mt5_symbol
            api = self._connection_for(account)
            tick = api.symbol_info_tick(operational_symbol)

        if tick is None:
            raise ValueError(
                f"No existe precio ejecutable para {signal.symbol}."
            )
        if side == "BUY":
            execution_price = float(getattr(tick, "ask", 0.0) or 0.0)
            order_type = getattr(api, "ORDER_TYPE_BUY", 0)
        elif side == "SELL":
            execution_price = float(getattr(tick, "bid", 0.0) or 0.0)
            order_type = getattr(api, "ORDER_TYPE_SELL", 1)
        else:
            raise ValueError("La dirección debe ser BUY o SELL.")
        if execution_price <= 0:
            raise ValueError(
                f"No existe precio ejecutable válido para {signal.symbol}."
            )

        calculated_loss = api.order_calc_profit(
            order_type,
            operational_symbol,
            1.0,
            execution_price,
            float(signal.stop_loss),
        )
        if calculated_loss is None:
            raise ValueError(
                "MT5 no pudo calcular la pérdida desde el precio actual "
                "hasta el Stop Loss."
            )
        return symbol_info, execution_price, abs(float(calculated_loss))

    def _calculate_profile_sizing(self, signal, profile, account):
        self._refresh_destination_metrics(account)
        symbol_info, execution_price, loss_per_lot = (
            self._execution_risk_context(signal, profile, account)
        )
        result = self._get_sizing_service().calculate(
            profile=profile,
            account=account,
            symbol=signal.symbol,
            direction=signal.direction,
            entry=execution_price,
            stop_loss=signal.stop_loss,
            symbol_info=symbol_info,
            loss_per_lot=loss_per_lot,
            signal_entry_price=signal.entry,
        )
        details = result.to_dict()
        details["profile_id"] = getattr(profile, "id", None)
        details["mt5_account_id"] = getattr(account, "id", None)
        details["symbol"] = signal.symbol
        details["stop_loss"] = signal.stop_loss
        details["risk_price_source"] = "CURRENT_MARKET"
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
