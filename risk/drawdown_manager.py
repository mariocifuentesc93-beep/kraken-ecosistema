class DrawdownManager:

    def __init__(self):

        self.enabled = True

        self.max_drawdown_percent = 10.0

        self.current_drawdown = 0.0

    def update(self, balance, equity):

        if balance <= 0:
            self.current_drawdown = 0
            return

        self.current_drawdown = (
            (balance - equity) / balance
        ) * 100

    def exceeded(self):

        if not self.enabled:
            return False

        return (
            self.current_drawdown >=
            self.max_drawdown_percent
        )

    def get_summary(self):

        return {
            "enabled": self.enabled,
            "current_drawdown": round(
                self.current_drawdown,
                2,
            ),
            "max_drawdown_percent":
                self.max_drawdown_percent,
        }


drawdown_manager = DrawdownManager()