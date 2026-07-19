class ExposureManager:

    def __init__(self):

        self.enabled = True

        self.max_open_trades = 5
        self.max_trades_per_symbol = 2
        self.max_buy_trades = 3
        self.max_sell_trades = 3

    def get_summary(self):

        return {
            "enabled": self.enabled,
            "max_open_trades": self.max_open_trades,
            "max_trades_per_symbol": self.max_trades_per_symbol,
            "max_buy_trades": self.max_buy_trades,
            "max_sell_trades": self.max_sell_trades,
        }


exposure_manager = ExposureManager()