import MetaTrader5 as mt5

from core.config_service import get_symbol


class PositionManager:

    def get_positions(self, symbol=None):

        if symbol is None:
            return mt5.positions_get()

        configured_symbol = get_symbol(symbol)
        mt5_symbol = (
            configured_symbol.mt5_symbol
            if configured_symbol is not None
            else symbol
        )

        return mt5.positions_get(symbol=mt5_symbol)

    def get_position(self, ticket):

        positions = mt5.positions_get(ticket=ticket)

        if positions is None:
            return None

        if len(positions) == 0:
            return None

        return positions[0]

    def close_position(self, ticket):

        position = self.get_position(ticket)

        if position is None:
            return False

        symbol = position.symbol

        tick = mt5.symbol_info_tick(symbol)

        if position.type == mt5.ORDER_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "position": ticket,
            "volume": position.volume,
            "type": order_type,
            "price": price,
            "deviation": 20,
            "magic": 10001,
            "comment": "TCC BOT CLOSE",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        return result

    def total_positions(self):

        positions = mt5.positions_get()

        if positions is None:
            return 0

        return len(positions)


position_manager = PositionManager()
