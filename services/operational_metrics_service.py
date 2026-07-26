from __future__ import annotations

from datetime import datetime, timedelta, timezone

from services.operational_data import OperationalData


class OperationalMetricsService:
    PERIODS = {"SESSION": None, "TODAY": 0, "7D": 7, "30D": 30}

    def __init__(self, data=None, session_started_at=None):
        self.data = data or OperationalData()
        self.session_started_at = session_started_at or datetime.now(timezone.utc)

    def calculate(self, period="TODAY"):
        since = self._since(period)
        clause = " AND datetime(created_at) >= datetime(?)" if since else ""
        params = (since,) if since else ()
        signal_count = self.data.scalar(
            f"SELECT COUNT(*) FROM signals WHERE 1=1{clause}", params
        )
        publications = self.data.scalar(
            f"SELECT COUNT(*) FROM telegram_publications WHERE status='SENT'{clause}",
            params,
        )
        operation_clause = clause.replace("created_at", "opened_at")
        simulations = self.data.scalar(
            f"""
            SELECT COUNT(*) FROM operations
            WHERE UPPER(status) IN ('SIMULATED','OPEN','CLOSED'){operation_clause}
            """,
            params,
        )
        logs = self._log_metrics(since)
        avg = self.data.scalar(
            """
            SELECT AVG(duration_ms) FROM operational_events
            WHERE duration_ms IS NOT NULL
            """ + (" AND datetime(timestamp) >= datetime(?)" if since else ""),
            params, default=0,
        ) if self.data.table_exists("operational_events") else 0
        return {
            "period": period, "signals_detected": signal_count,
            "signals_persisted": signal_count, "telegram_publications": publications,
            "simulations": simulations, "risk_rejections": logs["risk"],
            "preflight_blocks": logs["preflight"], "orders_sent": logs["sent"],
            "orders_filled": logs["filled"], "failures": logs["failures"],
            "duplicates_blocked": logs["duplicates"],
            "average_processing_ms": round(float(avg or 0), 1),
        }

    def _since(self, period):
        period = str(period).upper()
        now = datetime.now(timezone.utc)
        if period == "SESSION":
            return self.session_started_at.isoformat(timespec="seconds")
        days = self.PERIODS.get(period, 0)
        if days == 0:
            return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        return (now - timedelta(days=days)).isoformat(timespec="seconds")

    def _log_metrics(self, since):
        where = "WHERE datetime(created_at) >= datetime(?)" if since else ""
        rows = self.data.rows(
            f"SELECT UPPER(message) AS message FROM logs {where}",
            (since,) if since else (),
        )
        messages = [row["message"] or "" for row in rows]
        return {
            "risk": sum("RISK_REJECTED" in item for item in messages),
            "preflight": sum("PREFLIGHT" in item and "BLOCK" in item for item in messages),
            "sent": sum("ORDER" in item and "SENT" in item for item in messages),
            "filled": sum("FILLED" in item for item in messages),
            "failures": sum("FAILED" in item or "ERROR" in item for item in messages),
            "duplicates": sum("DUPLICATE" in item for item in messages),
        }
