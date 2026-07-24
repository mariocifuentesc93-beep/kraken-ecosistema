from datetime import datetime

from database.database_manager import database_manager
from models.telegram_channel import TelegramChannel


class TelegramChannelRepository:
    def __init__(self, connection_provider=None):
        self._connection_provider = connection_provider

    def _connection(self):
        provider = self._connection_provider
        if provider is None:
            return database_manager.connect()
        if hasattr(provider, "execute"):
            return provider
        return provider() if callable(provider) else provider

    def schema_available(self):
        row = self._connection().execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='telegram_channels'"
        ).fetchone()
        return row is not None

    @staticmethod
    def _from_row(row):
        return TelegramChannel(**dict(row)) if row else None

    def get_by_id(self, channel_id):
        if not self.schema_available():
            return None
        row = self._connection().execute(
            "SELECT * FROM telegram_channels WHERE id=?", (channel_id,)
        ).fetchone()
        return self._from_row(row)

    def get_by_identity(self, account_id, chat_id):
        if not self.schema_available():
            return None
        row = self._connection().execute(
            """
            SELECT * FROM telegram_channels
            WHERE telegram_account_id=? AND chat_id=?
            """,
            (account_id, chat_id),
        ).fetchone()
        return self._from_row(row)

    def list_by_account(self, account_id, include_unavailable=True):
        if account_id is None or not self.schema_available():
            return []
        sql = "SELECT * FROM telegram_channels WHERE telegram_account_id=?"
        if not include_unavailable:
            sql += " AND available=1"
        sql += " ORDER BY name COLLATE NOCASE, chat_id"
        rows = self._connection().execute(sql, (account_id,)).fetchall()
        return [self._from_row(row) for row in rows]

    def list_sendable(self, account_id):
        if account_id is None or not self.schema_available():
            return []
        rows = self._connection().execute(
            """
            SELECT * FROM telegram_channels
            WHERE telegram_account_id=?
              AND enabled=1 AND available=1 AND can_send=1
            ORDER BY name COLLATE NOCASE, chat_id
            """,
            (account_id,),
        ).fetchall()
        return [self._from_row(row) for row in rows]

    def set_enabled(self, channel_id, enabled):
        connection = self._connection()
        cursor = connection.execute(
            """
            UPDATE telegram_channels
            SET enabled=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (int(bool(enabled)), channel_id),
        )
        connection.commit()
        return cursor.rowcount > 0

    def synchronize(self, account_id, dialogs, synchronized_at=None):
        if not self.schema_available():
            raise RuntimeError(
                "El catálogo Telegram no está migrado. Ejecute la migración explícita."
            )
        timestamp = synchronized_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        connection = self._connection()
        seen = set()
        try:
            for dialog in dialogs:
                chat_id = int(dialog["chat_id"])
                seen.add(chat_id)
                connection.execute(
                    """
                    INSERT INTO telegram_channels (
                        telegram_account_id, chat_id, name, username, chat_type,
                        can_read, can_send, enabled, available, last_synced_at,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?, ?)
                    ON CONFLICT(telegram_account_id, chat_id) DO UPDATE SET
                        name=excluded.name,
                        username=excluded.username,
                        chat_type=excluded.chat_type,
                        can_read=excluded.can_read,
                        can_send=excluded.can_send,
                        available=1,
                        last_synced_at=excluded.last_synced_at,
                        updated_at=excluded.updated_at
                    """,
                    (
                        account_id, chat_id,
                        dialog.get("name") or str(chat_id),
                        dialog.get("username") or None,
                        dialog.get("chat_type") or "UNKNOWN",
                        int(bool(dialog.get("can_read", True))),
                        int(bool(dialog.get("can_send", False))),
                        timestamp, timestamp, timestamp,
                    ),
                )
            if seen:
                placeholders = ",".join("?" for _ in seen)
                connection.execute(
                    f"""
                    UPDATE telegram_channels
                    SET available=0, updated_at=?
                    WHERE telegram_account_id=?
                      AND chat_id NOT IN ({placeholders})
                    """,
                    [timestamp, account_id, *sorted(seen)],
                )
            else:
                connection.execute(
                    """
                    UPDATE telegram_channels
                    SET available=0, updated_at=?
                    WHERE telegram_account_id=?
                    """,
                    (timestamp, account_id),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        return self.list_by_account(account_id)


telegram_channel_repository = TelegramChannelRepository()
