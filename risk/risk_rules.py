class RiskRules:

    def __init__(self):

        self.enabled = True

        self.allow_multiple_same_symbol = False

        self.allow_opposite_trades = False

        self.block_after_daily_loss = True

        self.block_after_drawdown = True

        self.block_outside_schedule = True

        self.block_high_spread = True

    def get_summary(self):

        return {
            "enabled": self.enabled,
            "allow_multiple_same_symbol": self.allow_multiple_same_symbol,
            "allow_opposite_trades": self.allow_opposite_trades,
            "block_after_daily_loss": self.block_after_daily_loss,
            "block_after_drawdown": self.block_after_drawdown,
            "block_outside_schedule": self.block_outside_schedule,
            "block_high_spread": self.block_high_spread,
        }


risk_rules = RiskRules()