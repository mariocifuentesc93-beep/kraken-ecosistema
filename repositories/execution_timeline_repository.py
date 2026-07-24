from datetime import datetime

from database.database_manager import database_manager


class ExecutionTimelineRepository:
    def record(self, operation, previous_state, new_state, reason, execution_mode):
        cursor = database_manager.cursor()
        cursor.execute(
            """
            INSERT INTO operation_events(
                operation_id, event, description, created_at, previous_state,
                new_state, profile_id, symbol, execution_mode
            ) VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (operation.id, new_state, reason, datetime.now().isoformat(sep=" ", timespec="seconds"),
             previous_state or "", new_state, operation.profile_id, operation.symbol,
             execution_mode),
        )
        database_manager.commit()
        return cursor.lastrowid

    def get_all(self, symbol=None, profile_id=None, state=None):
        clauses, params = [], []
        if symbol:
            clauses.append("symbol=?"); params.append(symbol)
        if profile_id:
            clauses.append("profile_id=?"); params.append(profile_id)
        if state:
            clauses.append("new_state=?"); params.append(state)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        cursor = database_manager.cursor()
        cursor.execute("SELECT * FROM operation_events" + where + " ORDER BY id", params)
        return [dict(row) for row in cursor.fetchall()]

    def statistics(self):
        events = self.get_all()
        total = len(events)
        counts = {state: sum(event["new_state"] == state for event in events)
                  for state in ("REJECTED", "SIMULATED", "TP1", "TP2", "TP3", "CLOSED")}
        simulated = counts["SIMULATED"] or 1
        return {
            "rejection_rate": round(counts["REJECTED"] / total * 100, 2) if total else 0.0,
            "simulation_success_rate": round(counts["CLOSED"] / simulated * 100, 2),
            "tp1_percentage": round(counts["TP1"] / simulated * 100, 2),
            "tp2_percentage": round(counts["TP2"] / simulated * 100, 2),
            "tp3_percentage": round(counts["TP3"] / simulated * 100, 2),
            "average_execution_time": 0.0,
            "average_trade_duration": 0.0,
        }


execution_timeline_repository = ExecutionTimelineRepository()
