from mt5.executor import mt5_executor


class TrailingStop:

    def __init__(self):

        self.enabled = True

        self.trigger_points = 30

        self.step_points = 10

    # ---------------------------------------------------------

    def check(self, operation):

        if not self.enabled:

            return False

        if operation.status != "OPEN":

            return False

        if operation.pips < self.trigger_points:

            return False

        if operation.signal.direction == "BUY":

            new_sl = operation.current_price - self.step_points

            if operation.stop_loss >= new_sl:

                return False

        else:

            new_sl = operation.current_price + self.step_points

            if operation.stop_loss <= new_sl:

                return False

        result = mt5_executor.modify_position(

            ticket=operation.ticket,

            sl=new_sl,

            tp=operation.signal.take_profits[0],

            mt5_account_id=operation.mt5_account_id,

        )

        if not result:

            return False

        operation.stop_loss = new_sl

        operation.metadata["trailing"] = True

        print(

            f"✅ Trailing Stop actualizado {operation.ticket}"

        )

        return True

    # ---------------------------------------------------------

    def get_summary(self):

        return {

            "enabled": self.enabled,

            "trigger_points": self.trigger_points,

            "step_points": self.step_points,

        }


trailing_stop = TrailingStop()
