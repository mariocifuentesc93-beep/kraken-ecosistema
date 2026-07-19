from datetime import datetime

from database.database_manager import database_manager


class MarketPriceEventRepository:
    def record(self, operation, quote, event):
        cursor = database_manager.cursor()
        cursor.execute(
            """INSERT INTO simulation_price_events(
                operation_id, symbol, bid, ask, last_price, source, event, created_at
            ) VALUES (?,?,?,?,?,?,?,?)""",
            (operation.id, quote.get("symbol", operation.symbol), quote.get("bid"),
             quote.get("ask"), quote.get("last"), quote.get("source", "NONE"), event,
             datetime.now().isoformat(sep=" ", timespec="seconds")),
        )
        database_manager.commit()
        return cursor.lastrowid

    def get_all(self, operation_id=None):
        sql, params = "SELECT * FROM simulation_price_events", []
        if operation_id is not None:
            sql += " WHERE operation_id=?"; params.append(operation_id)
        cursor = database_manager.cursor()
        cursor.execute(sql + " ORDER BY id", params)
        return [dict(row) for row in cursor.fetchall()]


market_price_event_repository = MarketPriceEventRepository()
