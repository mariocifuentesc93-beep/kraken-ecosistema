import MetaTrader5 as mt5

class MT5Executor:

    DEFAULT_DEVIATION = 20

    def __init__(self, connection_registry=None):
        self._connection_registry = connection_registry
        self.last_error = ""

    def _connection(self, account):
        if account is None:
            self.last_error = "La operación no especifica una cuenta MT5."
            return None
        if self._connection_registry is None:
            from services.mt5_connection_registry import (
                mt5_connection_registry,
            )

            self._connection_registry = mt5_connection_registry
        try:
            return self._connection_registry.connection_for(
                account.id,
                getattr(account, "mt5_terminal_id", None),
            )
        except Exception as error:
            self.last_error = str(error)
            return None

    @staticmethod
    def _account(account=None, mt5_account_id=None):
        if account is not None:
            return account
        if mt5_account_id is None:
            return None
        from repositories.mt5_account_repository import (
            mt5_account_repository,
        )

        return mt5_account_repository.get_by_id(mt5_account_id)

    def _operational_symbol(self, signal, profile, account):
        from services.symbol_catalog_service import symbol_catalog_service

        catalog_id = str(
            getattr(profile, "catalog_id", "")
            or "BRIDGE_SYNTHETICS"
        )
        resolved = symbol_catalog_service.resolve_symbol(
            canonical_symbol=signal.symbol,
            mt5_account_id=account.id,
            catalog_id=catalog_id,
            profile_id=getattr(profile, "id", None),
        )
        return resolved.mt5_symbol

    # =========================================================
    # OPEN MARKET
    # =========================================================

    def execute_market_order(
        self,
        signal,
        volume,
        account,
        profile=None,
        preflight_result=None,
    ):

        if preflight_result is None:
            from services.execution_preflight_service import (
                execution_preflight_service,
            )
            preflight_result = execution_preflight_service.validate(
                signal=signal,
                profile=profile,
                account=account,
                volume=volume,
                risk_result=(getattr(signal, "metadata", None) or {}).get(
                    "position_sizing"
                ),
            )

        if not preflight_result.allowed:
            print(
                "[MT5] Ejecución bloqueada por pre-flight: "
                f"{preflight_result.code} - {preflight_result.reason}"
            )
            return None

        if volume <= 0:

            print("[MT5] Volumen inválido.")
            return None

        api = self._connection(account)
        if api is None:

            print(
                f"[MT5] No fue posible abrir la conexión aislada "
                f"de {account.name}: {self.last_error}"
            )
            return None

        try:
            mt5_symbol = self._operational_symbol(
                signal, profile, account
            )
        except Exception as error:
            self.last_error = str(error)
            print(f"[MT5] {self.last_error}")
            return None
        symbol_info = api.symbol_info(mt5_symbol)

        if symbol_info is None:

            print(f"[MT5] Símbolo no encontrado: {signal.symbol}")
            return None

        mt5_symbol = getattr(symbol_info, "name", mt5_symbol)

        if not bool(getattr(symbol_info, "visible", False)):
            if not api.symbol_select(mt5_symbol, True):
                print(f"[MT5] No se pudo seleccionar {mt5_symbol}")
                return None

        price, order_type = self._market_price(
            api,
            mt5_symbol,
            signal.direction,
        )

        if price is None:

            print("[MT5] No fue posible obtener el precio.")
            return None

        magic = getattr(account, "custom_magic", 0)

        if not magic:
            magic = getattr(account, "magic_number", 10001)

        comment = getattr(account, "comment", "KRAKEN")

        deviation = getattr(
            account,
            "deviation",
            self.DEFAULT_DEVIATION,
        )

        tp = self._target_take_profit(signal, profile)

        request = {

            "action": api.TRADE_ACTION_DEAL,

            "symbol": mt5_symbol,

            "volume": float(volume),

            "type": order_type,

            "price": float(price),

            "sl": float(signal.stop_loss),

            "tp": float(tp) if tp else 0.0,

            "deviation": int(deviation),

            "magic": int(magic),

            "comment": comment,

            "type_time": api.ORDER_TIME_GTC,

            "type_filling": api.ORDER_FILLING_IOC,

        }

        print()
        print("=" * 60)
        print("📤 ENVIANDO ORDEN")
        print("=" * 60)
        print(f"Cuenta    : {account.name}")
        print(f"Símbolo   : {mt5_symbol}")
        print(f"Dirección : {signal.direction}")
        print(f"Lote      : {volume}")
        print(f"Entrada   : {price}")
        print(f"SL        : {signal.stop_loss}")
        print(f"TP        : {tp}")
        print(f"Magic     : {magic}")

        return self._send(api, request)

    @staticmethod
    def _target_take_profit(signal, profile=None):
        """Return the profile-selected final target (TP1, TP2 or TP3)."""
        take_profits = list(getattr(signal, "take_profits", None) or [])
        if not take_profits:
            return None

        level = getattr(profile, "tp_level", 1) if profile is not None else 1
        try:
            level = int(level)
        except (TypeError, ValueError):
            level = 1

        index = min(max(level, 1), len(take_profits)) - 1
        return take_profits[index]

    # =========================================================

    def modify_position(
        self,
        ticket,
        sl=None,
        tp=None,
        account=None,
        mt5_account_id=None,
    ):
        account = self._account(account, mt5_account_id)
        api = self._connection(account)
        if api is None:
            return None

        request = {

            "action": api.TRADE_ACTION_SLTP,

            "position": ticket,

            "sl": sl,

            "tp": tp,

        }

        return self._send(api, request)

    # =========================================================

    def close_position(
        self,
        ticket,
        account=None,
        mt5_account_id=None,
    ):
        account = self._account(account, mt5_account_id)
        api = self._connection(account)
        if api is None:
            return None

        positions = api.positions_get(ticket=ticket)

        if not positions:

            return None

        position = positions[0]

        direction = (
            "SELL"
            if position.type == mt5.ORDER_TYPE_BUY
            else "BUY"
        )

        price, order_type = self._market_price(
            api,
            position.symbol,
            direction,
        )

        request = {

            "action": api.TRADE_ACTION_DEAL,

            "position": ticket,

            "symbol": position.symbol,

            "volume": position.volume,

            "type": order_type,

            "price": price,

            "deviation": self.DEFAULT_DEVIATION,

            "magic": position.magic,

            "comment": "KRAKEN CLOSE",

            "type_time": api.ORDER_TIME_GTC,

            "type_filling": api.ORDER_FILLING_IOC,

        }

        return self._send(api, request)

    # =========================================================

    def partial_close(
        self,
        ticket,
        volume,
        account=None,
        mt5_account_id=None,
    ):
        account = self._account(account, mt5_account_id)
        api = self._connection(account)
        if api is None:
            return None

        positions = api.positions_get(ticket=ticket)

        if not positions:

            return None

        position = positions[0]

        direction = (
            "SELL"
            if position.type == mt5.ORDER_TYPE_BUY
            else "BUY"
        )

        price, order_type = self._market_price(
            api,
            position.symbol,
            direction,
        )

        request = {

            "action": api.TRADE_ACTION_DEAL,

            "position": ticket,

            "symbol": position.symbol,

            "volume": volume,

            "type": order_type,

            "price": price,

            "deviation": self.DEFAULT_DEVIATION,

            "magic": position.magic,

            "comment": "KRAKEN PARTIAL",

            "type_time": api.ORDER_TIME_GTC,

            "type_filling": api.ORDER_FILLING_IOC,

        }

        return self._send(api, request)

    # =========================================================

    def _market_price(
        self,
        api,
        symbol,
        direction,
    ):

        direction = str(direction).upper()
        tick = api.symbol_info_tick(symbol)
        if tick is None:
            return None, None

        if direction == "BUY":

            return tick.ask, api.ORDER_TYPE_BUY

        return tick.bid, api.ORDER_TYPE_SELL

    # =========================================================

    def _send(
        self,
        api,
        request,
    ):

        result = api.order_send(request)

        if result is None:

            self.last_error = str(api.last_error())
            print("[MT5]", self.last_error)

            return None

        accepted_retcodes = {
            int(getattr(api, "TRADE_RETCODE_PLACED", 10008)),
            int(getattr(api, "TRADE_RETCODE_DONE", 10009)),
            int(getattr(api, "TRADE_RETCODE_DONE_PARTIAL", 10010)),
        }
        invalid_fill = int(
            getattr(api, "TRADE_RETCODE_INVALID_FILL", 10030)
        )

        # A symbol may reject IOC even though all pre-flight checks pass.
        # Retrying is safe only for INVALID_FILL because MT5 did not accept
        # the original order.
        if int(result.retcode) == invalid_fill:
            attempted = {int(request.get("type_filling", -1))}
            for filling_mode in (
                int(getattr(api, "ORDER_FILLING_FOK", 0)),
                int(getattr(api, "ORDER_FILLING_RETURN", 2)),
            ):
                if filling_mode in attempted:
                    continue
                attempted.add(filling_mode)
                retry_request = dict(request)
                retry_request["type_filling"] = filling_mode
                result = api.order_send(retry_request)
                if result is None:
                    self.last_error = str(api.last_error())
                    continue
                if int(result.retcode) in accepted_retcodes:
                    break
                if int(result.retcode) != invalid_fill:
                    break

        if result is None:
            if not self.last_error:
                self.last_error = str(api.last_error())
            print("[MT5]", self.last_error)
            return None

        if int(result.retcode) not in accepted_retcodes:

            print()
            print("=" * 60)
            print("❌ MT5 ERROR")
            print("=" * 60)
            print(f"RetCode : {result.retcode}")
            print(f"Comment : {result.comment}")
            self.last_error = (
                f"retcode={result.retcode}; comment={result.comment}"
            )

            return None

        print()
        print("=" * 60)
        print("✅ ORDEN EJECUTADA")
        print("=" * 60)
        print(f"Ticket : {result.order}")
        print(f"Deal   : {result.deal}")
        print(f"Precio : {result.price}")

        self.last_error = ""
        return result


mt5_executor = MT5Executor()
