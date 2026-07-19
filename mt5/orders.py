import MetaTrader5 as mt5


class OrderManager:

    def get_orders(self):
        orders = mt5.orders_get()

        if orders is None:
            return []

        return list(orders)

    def get_order(self, ticket):
        orders = mt5.orders_get(ticket=ticket)

        if orders is None or len(orders) == 0:
            return None

        return orders[0]

    def cancel_order(self, ticket):

        order = self.get_order(ticket)

        if order is None:
            return False

        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": ticket,
            "magic": 10001,
            "comment": "TCC BOT CANCEL",
        }

        result = mt5.order_send(request)

        return result

    def total_orders(self):

        orders = mt5.orders_get()

        if orders is None:
            return 0

        return len(orders)


order_manager = OrderManager()