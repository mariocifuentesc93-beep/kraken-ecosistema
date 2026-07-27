from collections import defaultdict
from datetime import date

from database.database_manager import database_manager
from services.trading_analytics_service import trading_analytics_service


class SymbolRankingService:
    """Aggregate real operation milestones by symbol using shared report filters."""

    def ranking(self, filters=None):
        filters = filters or {}
        records = [
            row for row in trading_analytics_service.records(filters)
            if str(row.get("id", "")).startswith("O")
            and row.get("status") in {"OPEN", "CLOSED"}
        ]
        operation_ids = [int(row["id"][1:]) for row in records]
        milestones = defaultdict(set)
        if operation_ids:
            placeholders = ",".join("?" for _ in operation_ids)
            rows = database_manager.execute(
                f"""
                SELECT operation_id,new_state FROM operation_events
                WHERE operation_id IN ({placeholders})
                  AND new_state IN ('TP1','TP2','TP3','SL')
                """,
                tuple(operation_ids),
            ).fetchall()
            for row in rows:
                milestones[row["operation_id"]].add(row["new_state"])

        grouped = defaultdict(lambda: {
            "operations": 0, "tp1": 0, "tp2": 0, "tp3": 0, "sl": 0,
            "wins": 0, "losses": 0, "net": 0.0,
        })
        for row in records:
            item = grouped[row["symbol"]]
            item["operations"] += 1
            item["net"] += float(row.get("net") or 0.0)
            item["wins"] += float(row.get("net") or 0.0) > 0
            item["losses"] += float(row.get("net") or 0.0) < 0
            reached = milestones[int(row["id"][1:])]
            for key in ("tp1", "tp2", "tp3", "sl"):
                item[key] += key.upper() in reached

        result = []
        for symbol, item in grouped.items():
            total = item["operations"]
            row = {
                "symbol": symbol,
                **item,
                "tp1_rate": round(item["tp1"] / total * 100, 2),
                "tp2_rate": round(item["tp2"] / total * 100, 2),
                "tp3_rate": round(item["tp3"] / total * 100, 2),
                "sl_rate": round(item["sl"] / total * 100, 2),
                "win_rate": round(item["wins"] / total * 100, 2),
            }
            row["score"] = round(
                row["tp1_rate"]
                + row["tp2_rate"] * 2
                + row["tp3_rate"] * 3
                - row["sl_rate"],
                2,
            )
            result.append(row)
        result.sort(
            key=lambda row: (
                row["score"], row["tp3_rate"], row["tp2_rate"],
                row["tp1_rate"], row["net"],
            ),
            reverse=True,
        )
        for index, row in enumerate(result, 1):
            row["rank"] = index
        return result


symbol_ranking_service = SymbolRankingService()
