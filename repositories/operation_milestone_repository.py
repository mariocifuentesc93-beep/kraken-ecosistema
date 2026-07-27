import json
from datetime import datetime

from database.database_manager import database_manager


MILESTONES = ("TP1", "TP2", "TP3", "SL")


class OperationMilestoneRepository:
    """Persist target definitions and reached levels in operation_events."""

    def save_levels(self, operation, execution_mode):
        take_profits = list(
            getattr(getattr(operation, "signal", None), "take_profits", None)
            or []
        )
        if not take_profits and operation.take_profit:
            take_profits = [operation.take_profit]
        payload = {
            "message": "Orden abierta en MT5",
            "tp1": take_profits[0] if len(take_profits) > 0 else 0.0,
            "tp2": take_profits[1] if len(take_profits) > 1 else 0.0,
            "tp3": take_profits[2] if len(take_profits) > 2 else 0.0,
            "stop_loss": float(operation.stop_loss or 0.0),
        }
        return self._insert(
            operation, "OPEN", json.dumps(payload, ensure_ascii=False),
            execution_mode,
        )

    def levels(self, operation):
        row = database_manager.execute(
            """
            SELECT description FROM operation_events
            WHERE operation_id=? AND new_state='OPEN'
            ORDER BY id DESC LIMIT 1
            """,
            (operation.id,),
        ).fetchone()
        payload = {}
        if row:
            try:
                payload = json.loads(row["description"] or "{}")
            except (TypeError, ValueError, json.JSONDecodeError):
                payload = {}
        return {
            "TP1": float(payload.get("tp1") or operation.take_profit or 0.0),
            "TP2": float(payload.get("tp2") or 0.0),
            "TP3": float(payload.get("tp3") or 0.0),
            "SL": float(payload.get("stop_loss") or operation.stop_loss or 0.0),
        }

    def reached(self, operation_id):
        rows = database_manager.execute(
            """
            SELECT DISTINCT new_state FROM operation_events
            WHERE operation_id=? AND new_state IN ('TP1','TP2','TP3','SL')
            """,
            (operation_id,),
        ).fetchall()
        return {row["new_state"] for row in rows}

    def record(self, operation, milestone, price, execution_mode):
        milestone = str(milestone).upper()
        if milestone not in MILESTONES:
            raise ValueError(f"Hito no soportado: {milestone}")
        cursor = database_manager.cursor()
        cursor.execute(
            """
            SELECT 1 FROM operation_events
            WHERE operation_id=? AND new_state=?
            LIMIT 1
            """,
            (operation.id, milestone),
        )
        if cursor.fetchone():
            return False
        self._insert(
            operation,
            milestone,
            json.dumps(
                {"milestone": milestone, "price": float(price)},
                ensure_ascii=False,
            ),
            execution_mode,
        )
        return True

    @staticmethod
    def _insert(operation, state, description, execution_mode):
        cursor = database_manager.cursor()
        cursor.execute(
            """
            INSERT INTO operation_events(
                operation_id, event, description, created_at, previous_state,
                new_state, profile_id, symbol, execution_mode
            ) VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                operation.id, state, description,
                datetime.now().isoformat(sep=" ", timespec="seconds"),
                "", state, operation.profile_id, operation.symbol,
                str(execution_mode or "UNKNOWN").upper(),
            ),
        )
        database_manager.commit()
        return cursor.lastrowid


operation_milestone_repository = OperationMilestoneRepository()
