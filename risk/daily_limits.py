class DailyLimits:

    def __init__(self):

        self.enabled = True

        self.max_daily_loss_percent = 5.0
        self.max_daily_profit_percent = 10.0

        self.max_consecutive_losses = 3
        self.max_consecutive_wins = 10

        self.max_open_trades = 5

    def get_summary(self):

        return {
            "enabled": self.enabled,
            "max_daily_loss_percent": self.max_daily_loss_percent,
            "max_daily_profit_percent": self.max_daily_profit_percent,
            "max_consecutive_losses": self.max_consecutive_losses,
            "max_consecutive_wins": self.max_consecutive_wins,
            "max_open_trades": self.max_open_trades,
        }


daily_limits = DailyLimits()