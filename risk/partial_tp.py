from mt5.executor import mt5_executor


class PartialTP:

    def __init__(self):

        self.enabled = True

        self.levels = [

            {
                "tp": 1,
                "close_percent": 30,
            },

            {
                "tp": 2,
                "close_percent": 30,
            },

            {
                "tp": 3,
                "close_percent": 40,
            },

        ]

    # ---------------------------------------------------------

    def check(self, operation):

        if not self.enabled:

            return False

        if operation.status != "OPEN":

            return False

        executed = False

        for level in self.levels:

            tp_index = level["tp"] - 1

            if tp_index >= len(operation.signal.take_profits):

                continue

            key = f"tp{level['tp']}"

            if operation.metadata.get(key):

                continue

            target = operation.signal.take_profits[tp_index]

            reached = False

            if operation.signal.direction == "BUY":

                reached = operation.current_price >= target

            else:

                reached = operation.current_price <= target

            if not reached:

                continue

            volume = round(

                operation.volume
                * level["close_percent"]
                / 100,

                2,

            )

            result = mt5_executor.partial_close(

                operation.ticket,

                volume,

                mt5_account_id=operation.mt5_account_id,

            )

            if not result:

                continue

            operation.metadata[key] = True

            operation.volume -= volume

            executed = True

            print(

                f"✅ TP{level['tp']} ejecutado | Ticket {operation.ticket}"

            )

        return executed

    # ---------------------------------------------------------

    def reset(self):

        for level in self.levels:

            level["executed"] = False

    # ---------------------------------------------------------

    def get_summary(self):

        return {

            "enabled": self.enabled,

            "levels": self.levels,

        }


partial_tp = PartialTP()
