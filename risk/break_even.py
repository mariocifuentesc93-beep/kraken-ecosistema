from mt5.executor import mt5_executor


class BreakEven:

    def __init__(self):

        self.enabled = True

        self.trigger_points = 20

        self.offset_points = 0

    # ---------------------------------------------------------

    def check(self, operation):

        if not self.enabled:

            return False

        if operation.status != "OPEN":

            return False

        if operation.metadata.get("break_even"):

            return False

        if operation.pips < self.trigger_points:

            return False

        if operation.signal.direction == "BUY":

            new_sl = (

                operation.signal.entry

                + self.offset_points
            )

        else:

            new_sl = (

                operation.signal.entry

                - self.offset_points
            )

        result = mt5_executor.modify_position(

            operation.ticket,

            sl=new_sl,

            tp=operation.signal.take_profits[0],

        )

        if result:

            operation.metadata["break_even"] = True

            print(

                f"✅ Break Even aplicado {operation.ticket}"

            )

            return True

        return False

    # ---------------------------------------------------------

    def get_summary(self):

        return {

            "enabled": self.enabled,

            "trigger_points": self.trigger_points,

            "offset_points": self.offset_points,

        }


break_even = BreakEven()