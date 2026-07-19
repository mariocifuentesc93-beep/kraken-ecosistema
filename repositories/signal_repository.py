import json
from datetime import datetime, timedelta

from database.database_manager import database_manager
from models.signal import Signal


class SignalRepository:
    def create(self, signal):
        cursor = database_manager.cursor()
        cursor.execute(
            """
            INSERT INTO signals (
                telegram_account_id, profile_id, symbol, direction, entry,
                stop_loss, tp1, tp2, tp3, market_execution, raw_message,
                status, created_at, source, message_id, score, rejection_reason,
                parsed_fields, trade_request, execution_decision
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                signal.telegram_account_id, signal.profile_id, signal.symbol,
                signal.direction, signal.entry, signal.stop_loss, signal.tp1,
                signal.tp2, signal.tp3, int(bool(signal.market_execution)),
                signal.raw_message, signal.status,
                signal.received_at.isoformat(sep=" ", timespec="seconds"),
                signal.source, signal.message_id, signal.score,
                signal.rejection_reason,
                json.dumps(signal.metadata, ensure_ascii=False),
                json.dumps(signal.metadata.get("trade_request", {}), ensure_ascii=False),
                signal.execution_decision,
            ),
        )
        database_manager.commit()
        signal.id = cursor.lastrowid
        return signal

    def get_all(self):
        cursor = database_manager.cursor()
        cursor.execute("SELECT * FROM signals ORDER BY id DESC")
        return [self._from_row(dict(row)) for row in cursor.fetchall()]

    def get_by_id(self, signal_id):
        cursor = database_manager.cursor()
        cursor.execute("SELECT * FROM signals WHERE id=?", (signal_id,))
        row = cursor.fetchone()
        return self._from_row(dict(row)) if row else None

    def is_duplicate(self, raw_message, chat_id=None, seconds=300):
        threshold = (datetime.now() - timedelta(seconds=seconds)).isoformat(
            sep=" ", timespec="seconds"
        )
        cursor = database_manager.cursor()
        cursor.execute(
            """
            SELECT 1 FROM signals
            WHERE raw_message=? AND created_at>=?
            LIMIT 1
            """,
            (raw_message, threshold),
        )
        return cursor.fetchone() is not None

    @staticmethod
    def _from_row(row):
        metadata = json.loads(row.pop("parsed_fields", "{}") or "{}")
        trade_request = json.loads(row.pop("trade_request", "{}") or "{}")
        metadata["trade_request"] = trade_request
        signal = Signal(
            id=row.get("id"), source=row.get("source") or "Telegram",
            message_id=row.get("message_id"),
            telegram_account_id=row.get("telegram_account_id"),
            profile_id=row.get("profile_id"), symbol=row.get("symbol") or "",
            direction=row.get("direction") or "", entry=row.get("entry") or 0,
            stop_loss=row.get("stop_loss") or 0,
            take_profits=[value for value in (row.get("tp1"), row.get("tp2"), row.get("tp3")) if value],
            market_execution=bool(row.get("market_execution")),
            raw_message=row.get("raw_message") or "", score=row.get("score") or 0,
            status=row.get("status") or "NEW",
            rejection_reason=row.get("rejection_reason") or "",
            execution_decision=row.get("execution_decision") or "",
            metadata=metadata,
        )
        return signal


signal_repository = SignalRepository()
