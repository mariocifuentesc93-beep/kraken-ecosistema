import MetaTrader5 as mt5

from mt5.connector import mt5_connector
from mt5.symbols import (
    select_symbol,
    get_ask,
    get_bid,
    get_symbol_info,
)


class MT5Executor:

    DEFAULT_DEVIATION = 20

    # =========================================================
    # OPEN MARKET
    # =========================================================

    def execute_market_order(
        self,
        signal,
        volume,
        account,
    ):

        if volume <= 0:

            print("[MT5] Volumen inválido.")
            return None

        if not mt5_connector.login(account):

            print(f"[MT5] No fue posible conectar la cuenta {account.name}")
            return None

        symbol_info = get_symbol_info(signal.symbol)

        if symbol_info is None:

            print(f"[MT5] Símbolo no encontrado: {signal.symbol}")
            return None

        mt5_symbol = symbol_info.name

        if not select_symbol(signal.symbol):

            print(f"[MT5] No se pudo seleccionar {mt5_symbol}")
            return None

        price, order_type = self._market_price(
            signal.symbol,
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

        tp = None

        if hasattr(signal, "take_profits"):

            if signal.take_profits:

                tp = signal.take_profits[0]

        request = {

            "action": mt5.TRADE_ACTION_DEAL,

            "symbol": mt5_symbol,

            "volume": float(volume),

            "type": order_type,

            "price": float(price),

            "sl": float(signal.stop_loss),

            "tp": float(tp) if tp else 0.0,

            "deviation": int(deviation),

            "magic": int(magic),

            "comment": comment,

            "type_time": mt5.ORDER_TIME_GTC,

            "type_filling": mt5.ORDER_FILLING_IOC,

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

        return self._send(request)

    # =========================================================

    def modify_position(
        self,
        ticket,
        sl=None,
        tp=None,
    ):

        request = {

            "action": mt5.TRADE_ACTION_SLTP,

            "position": ticket,

            "sl": sl,

            "tp": tp,

        }

        return self._send(request)

    # =========================================================

    def close_position(
        self,
        ticket,
    ):

        positions = mt5.positions_get(ticket=ticket)

        if not positions:

            return None

        position = positions[0]

        direction = (
            "SELL"
            if position.type == mt5.ORDER_TYPE_BUY
            else "BUY"
        )

        price, order_type = self._market_price(
            position.symbol,
            direction,
        )

        request = {

            "action": mt5.TRADE_ACTION_DEAL,

            "position": ticket,

            "symbol": position.symbol,

            "volume": position.volume,

            "type": order_type,

            "price": price,

            "deviation": self.DEFAULT_DEVIATION,

            "magic": position.magic,

            "comment": "KRAKEN CLOSE",

            "type_time": mt5.ORDER_TIME_GTC,

            "type_filling": mt5.ORDER_FILLING_IOC,

        }

        return self._send(request)

    # =========================================================

    def partial_close(
        self,
        ticket,
        volume,
    ):

        positions = mt5.positions_get(ticket=ticket)

        if not positions:

            return None

        position = positions[0]

        direction = (
            "SELL"
            if position.type == mt5.ORDER_TYPE_BUY
            else "BUY"
        )

        price, order_type = self._market_price(
            position.symbol,
            direction,
        )

        request = {

            "action": mt5.TRADE_ACTION_DEAL,

            "position": ticket,

            "symbol": position.symbol,

            "volume": volume,

            "type": order_type,

            "price": price,

            "deviation": self.DEFAULT_DEVIATION,

            "magic": position.magic,

            "comment": "KRAKEN PARTIAL",

            "type_time": mt5.ORDER_TIME_GTC,

            "type_filling": mt5.ORDER_FILLING_IOC,

        }

        return self._send(request)

    # =========================================================

    def _market_price(
        self,
        symbol,
        direction,
    ):

        direction = str(direction).upper()

        if direction == "BUY":

            return get_ask(symbol), mt5.ORDER_TYPE_BUY

        return get_bid(symbol), mt5.ORDER_TYPE_SELL

    # =========================================================

    def _send(
        self,
        request,
    ):

        result = mt5.order_send(request)

        if result is None:

            print("[MT5]", mt5.last_error())

            return None

        if result.retcode != mt5.TRADE_RETCODE_DONE:

            print()
            print("=" * 60)
            print("❌ MT5 ERROR")
            print("=" * 60)
            print(f"RetCode : {result.retcode}")
            print(f"Comment : {result.comment}")

            return None

        print()
        print("=" * 60)
        print("✅ ORDEN EJECUTADA")
        print("=" * 60)
        print(f"Ticket : {result.order}")
        print(f"Deal   : {result.deal}")
        print(f"Precio : {result.price}")

        return result


mt5_executor = MT5Executor()