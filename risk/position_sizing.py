from mt5.connector import mt5_connector


class PositionSizing:

    # ---------------------------------------------------------

    def calculate_by_percent(
        self,
        symbol,
        risk_percent,
        entry_price,
        stop_loss,
    ):

        balance = mt5_connector.get_balance()

        point = mt5_connector.get_point_value(symbol)

        volume_min = mt5_connector.get_volume_min(symbol)
        volume_max = mt5_connector.get_volume_max(symbol)
        volume_step = mt5_connector.get_volume_step(symbol)

        if balance <= 0:

            return 0

        if point is None or point <= 0:

            return 0

        stop_distance = abs(entry_price - stop_loss)

        if stop_distance <= 0:

            return 0

        risk_money = balance * (risk_percent / 100)

        lot = risk_money / (stop_distance * point)

        lot = self._normalize(
            lot,
            volume_min,
            volume_max,
            volume_step,
        )

        return lot

    # ---------------------------------------------------------

    def calculate_by_amount(
        self,
        symbol,
        risk_amount,
        entry_price,
        stop_loss,
    ):

        point = mt5_connector.get_point_value(symbol)

        volume_min = mt5_connector.get_volume_min(symbol)
        volume_max = mt5_connector.get_volume_max(symbol)
        volume_step = mt5_connector.get_volume_step(symbol)

        if point is None or point <= 0:

            return 0

        stop_distance = abs(entry_price - stop_loss)

        if stop_distance <= 0:

            return 0

        lot = risk_amount / (stop_distance * point)

        lot = self._normalize(
            lot,
            volume_min,
            volume_max,
            volume_step,
        )

        return lot

    # ---------------------------------------------------------

    def calculate_fixed(
        self,
        fixed_lot,
    ):

        return round(float(fixed_lot), 2)

    # ---------------------------------------------------------

    def _normalize(
        self,
        lot,
        volume_min,
        volume_max,
        volume_step,
    ):

        lot = max(volume_min, lot)
        lot = min(volume_max, lot)

        lot = round(lot / volume_step) * volume_step

        return round(lot, 2)


position_sizing = PositionSizing()