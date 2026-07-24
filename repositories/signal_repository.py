import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from models.signal import Signal


@dataclass(frozen=True)
class SignalCreateResult:
    signal: Signal
    created: bool

    @property
    def already_existed(self) -> bool:
        return not self.created


class SignalRepository:
    def __init__(self, database=None):
        self.database = database

    def _connection(self):
        if self.database is None:
            from database.database_manager import database_manager
            self.database = database_manager
        if isinstance(self.database, sqlite3.Connection):
            self.database.row_factory = sqlite3.Row
            return self.database
        return self.database.connect()

    @staticmethod
    def _datetime_text(value: Optional[datetime]) -> Optional[str]:
        return value.isoformat(timespec="microseconds") if value else None

    @staticmethod
    def _row_to_signal(row) -> Signal:
        values = dict(row)
        metadata = json.loads(values.get("metadata") or "{}")
        return Signal(
            id=values.get("id"),
            source=values.get("source") or "TELEGRAM",
            external_signal_id=values.get("external_signal_id"),
            idempotency_key=values.get("idempotency_key"),
            telegram_account_id=values.get("telegram_account_id"),
            chat_id=values.get("chat_id"),
            message_id=values.get("message_id"),
            received_at=values.get("received_at"),
            detected_at=values.get("detected_at"),
            symbol=values.get("symbol") or "",
            direction=values.get("direction") or "",
            entry=values.get("entry") or 0.0,
            stop_loss=values.get("stop_loss") or 0.0,
            take_profits=json.loads(values.get("take_profits") or "[]"),
            raw_message=values.get("raw_message") or "",
            metadata=metadata,
            status=values.get("status") or "NEW",
            score=values.get("score") or 0.0,
            rejection_reason=(
                values.get("rejection_reason")
                or metadata.get("rejection_reason")
                or ""
            ),
            execution_decision=(
                values.get("execution_decision")
                or metadata.get("execution_decision")
                or ""
            ),
            profile_id=values.get("profile_id"),
        )

    def create(self, signal: Signal) -> SignalCreateResult:
        signal.validate_persistent_identity()

        connection = self._connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO signals (
                    source, external_signal_id, idempotency_key,
                    telegram_account_id, chat_id, message_id,
                    received_at, detected_at, symbol, direction,
                    entry, stop_loss, take_profits, raw_message,
                    metadata, status, score, profile_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal.source,
                    signal.external_signal_id,
                    signal.idempotency_key,
                    signal.telegram_account_id,
                    signal.chat_id,
                    signal.message_id,
                    self._datetime_text(signal.received_at),
                    self._datetime_text(signal.detected_at),
                    signal.symbol,
                    signal.direction,
                    signal.entry,
                    signal.stop_loss,
                    json.dumps(signal.take_profits),
                    signal.raw_message,
                    json.dumps(signal.metadata, sort_keys=True),
                    signal.status,
                    signal.score,
                    signal.profile_id,
                ),
            )
            connection.commit()
            signal.id = cursor.lastrowid
            return SignalCreateResult(signal=signal, created=True)
        except sqlite3.IntegrityError as error:
            if "idempotency_key" not in str(error):
                connection.rollback()
                raise
            connection.rollback()
            existing = self.get_by_idempotency_key(signal.idempotency_key)
            if existing is None:
                raise
            return SignalCreateResult(signal=existing, created=False)

    def get_by_id(self, signal_id: int) -> Optional[Signal]:
        row = self._connection().execute(
            "SELECT * FROM signals WHERE id=?",
            (signal_id,),
        ).fetchone()
        return self._row_to_signal(row) if row else None

    def get_by_idempotency_key(self, key: str) -> Optional[Signal]:
        row = self._connection().execute(
            "SELECT * FROM signals WHERE idempotency_key=?",
            (key,),
        ).fetchone()
        return self._row_to_signal(row) if row else None

    def exists_by_idempotency_key(self, key: str) -> bool:
        row = self._connection().execute(
            "SELECT 1 FROM signals WHERE idempotency_key=? LIMIT 1",
            (key,),
        ).fetchone()
        return row is not None

    def list(self, limit=None):
        sql = "SELECT * FROM signals ORDER BY id DESC"
        parameters = ()
        if limit is not None:
            sql += " LIMIT ?"
            parameters = (limit,)
        rows = self._connection().execute(sql, parameters).fetchall()
        return [self._row_to_signal(row) for row in rows]

    def get_all(self):
        return self.list()

    def get_last(self, limit=100):
        return self.list(limit=limit)

    def get_by_profile(self, profile_id):
        rows = self._connection().execute(
            "SELECT * FROM signals WHERE profile_id=? ORDER BY id DESC",
            (profile_id,),
        ).fetchall()
        return [self._row_to_signal(row) for row in rows]

    def get_by_status(self, status):
        rows = self._connection().execute(
            "SELECT * FROM signals WHERE status=? ORDER BY id DESC",
            (status,),
        ).fetchall()
        return [self._row_to_signal(row) for row in rows]

    def get_by_telegram_account(self, telegram_account_id):
        rows = self._connection().execute(
            """
            SELECT * FROM signals
            WHERE telegram_account_id=?
            ORDER BY id DESC
            """,
            (telegram_account_id,),
        ).fetchall()
        return [self._row_to_signal(row) for row in rows]

    def update_status(self, signal_id, status):
        connection = self._connection()
        cursor = connection.execute(
            "UPDATE signals SET status=? WHERE id=?",
            (status, signal_id),
        )
        connection.commit()
        return cursor.rowcount > 0

    def update_profile(self, signal_id, profile_id):
        connection = self._connection()
        cursor = connection.execute(
            "UPDATE signals SET profile_id=? WHERE id=?",
            (profile_id, signal_id),
        )
        connection.commit()
        return cursor.rowcount > 0

    def delete(self, signal_id):
        connection = self._connection()
        cursor = connection.execute(
            "DELETE FROM signals WHERE id=?",
            (signal_id,),
        )
        connection.commit()
        return cursor.rowcount > 0

    def count(self):
        return self._connection().execute(
            "SELECT COUNT(*) FROM signals"
        ).fetchone()[0]

    def clear(self):
        connection = self._connection()
        connection.execute("DELETE FROM signals")
        connection.commit()


signal_repository = SignalRepository()
