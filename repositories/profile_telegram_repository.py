from database.database_manager import database_manager
from repositories.profile_repository import _profile_from_row
from repositories.telegram_channel_repository import telegram_channel_repository


class ProfileTelegramChannelRepository:
    """Profile/channel associations with a temporary legacy-schema fallback."""

    def __init__(self, connection_provider=None):
        self._connection_provider = connection_provider

    def _connection(self):
        provider = self._connection_provider
        if provider is None:
            return database_manager.connect()
        if hasattr(provider, "execute"):
            return provider
        return provider() if callable(provider) else provider

    def _uses_catalog(self):
        connection = self._connection()
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='telegram_channels'"
        ).fetchone()
        if table is None:
            return False
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(profile_telegram_channels)"
            ).fetchall()
        }
        return "telegram_channel_id" in columns

    def get_selected_channel_ids(self, profile_id):
        if not self._uses_catalog() or profile_id is None:
            return []
        rows = self._connection().execute(
            """
            SELECT telegram_channel_id
            FROM profile_telegram_channels
            WHERE profile_id=? AND enabled=1
            ORDER BY priority, id
            """,
            (profile_id,),
        ).fetchall()
        return [row[0] for row in rows]

    def set_profile_channels(self, profile_id, channel_ids):
        if not self._uses_catalog():
            raise RuntimeError(
                "El catálogo Telegram no está migrado. No se guardaron asociaciones."
            )
        channel_ids = list(dict.fromkeys(
            int(value) for value in channel_ids if value is not None
        ))
        connection = self._connection()
        try:
            connection.execute(
                "DELETE FROM profile_telegram_channels WHERE profile_id=?",
                (profile_id,),
            )
            for priority, channel_id in enumerate(channel_ids, start=1):
                connection.execute(
                    """
                    INSERT INTO profile_telegram_channels
                    (profile_id, telegram_channel_id, enabled, priority)
                    VALUES (?, ?, 1, ?)
                    """,
                    (profile_id, channel_id, priority),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    def get_channels_for_profile(self, profile_id):
        if not self._uses_catalog():
            return []
        rows = self._connection().execute(
            """
            SELECT c.*
            FROM telegram_channels c
            JOIN profile_telegram_channels pc
              ON pc.telegram_channel_id=c.id
            WHERE pc.profile_id=? AND pc.enabled=1
            ORDER BY pc.priority, c.name COLLATE NOCASE
            """,
            (profile_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_profiles(self, account_id, chat_id=None):
        if chat_id is None:
            chat_id = account_id
            account_id = None
        if not self._uses_catalog():
            query = """
                SELECT p.*
                FROM profiles p
                JOIN profile_telegram_channels c ON c.profile_id=p.id
                WHERE c.chat_id=? AND c.enabled=1 AND p.enabled=1
            """
            params = [chat_id]
            if account_id is not None:
                query += " AND c.account_id=?"
                params.append(account_id)
            query += " ORDER BY c.priority, p.name"
        else:
            query = """
                SELECT p.*
                FROM profiles p
                JOIN profile_telegram_channels pc ON pc.profile_id=p.id
                JOIN telegram_channels c ON c.id=pc.telegram_channel_id
                WHERE c.chat_id=?
                  AND pc.enabled=1 AND c.enabled=1 AND c.available=1
                  AND p.enabled=1
                  AND p.signal_source_mode IN ('TELEGRAM', 'BOTH')
            """
            params = [chat_id]
            if account_id is not None:
                query += " AND c.telegram_account_id=?"
                params.append(account_id)
            query += " ORDER BY pc.priority, p.name"
        rows = self._connection().execute(query, params).fetchall()
        return [_profile_from_row(row) for row in rows]

    def has_profiles(self, account_id, chat_id=None):
        return bool(self.get_profiles(account_id, chat_id))

    def count_profiles(self, account_id, chat_id=None):
        return len(self.get_profiles(account_id, chat_id))

    def get_available_channels(self, account_id):
        if self._uses_catalog():
            return [
                {
                    **channel.__dict__,
                    "title": channel.name,
                    "account_id": channel.telegram_account_id,
                }
                for channel in telegram_channel_repository.list_by_account(account_id)
            ]
        if account_id is None:
            return []
        rows = self._connection().execute(
            """
            SELECT chat_id, MAX(title) AS title, MAX(username) AS username
            FROM profile_telegram_channels
            WHERE account_id=?
            GROUP BY chat_id
            ORDER BY title, chat_id
            """,
            (account_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    # Legacy CRUD remains available until the explicit migration is applied.
    def create_channel(self, chat_id, title, profile_id=None, account_id=None):
        if self._uses_catalog():
            if profile_id is None or account_id is None:
                raise ValueError("profile_id and account_id are required")
            connection = self._connection()
            connection.execute(
                """
                INSERT INTO telegram_channels (
                    telegram_account_id, chat_id, name, chat_type,
                    can_read, can_send, enabled, available
                ) VALUES (?, ?, ?, 'UNKNOWN', 1, 0, 1, 1)
                ON CONFLICT(telegram_account_id, chat_id)
                DO UPDATE SET name=excluded.name, available=1
                """,
                (account_id, chat_id, title),
            )
            channel_id = connection.execute(
                """
                SELECT id FROM telegram_channels
                WHERE telegram_account_id=? AND chat_id=?
                """,
                (account_id, chat_id),
            ).fetchone()[0]
            connection.execute(
                """
                INSERT OR IGNORE INTO profile_telegram_channels
                (profile_id, telegram_channel_id, enabled, priority)
                VALUES (?, ?, 1, 1)
                """,
                (profile_id, channel_id),
            )
            connection.commit()
            return channel_id
        if profile_id is None or account_id is None:
            raise ValueError("profile_id and account_id are required")
        cursor = self._connection().execute(
            """
            INSERT INTO profile_telegram_channels
            (profile_id, account_id, chat_id, title, enabled, priority)
            VALUES (?, ?, ?, ?, 1, 1)
            """,
            (profile_id, account_id, chat_id, title),
        )
        self._connection().commit()
        return cursor.lastrowid

    def get_channel(self, chat_id):
        if self._uses_catalog():
            return None
        row = self._connection().execute(
            """
            SELECT * FROM profile_telegram_channels
            WHERE chat_id=? ORDER BY priority LIMIT 1
            """,
            (chat_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_by_id(self, channel_id):
        if self._uses_catalog():
            channel = telegram_channel_repository.get_by_id(channel_id)
            return channel.__dict__ if channel else None
        row = self._connection().execute(
            "SELECT * FROM profile_telegram_channels WHERE id=?", (channel_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_channels(self):
        if self._uses_catalog():
            rows = self._connection().execute(
                "SELECT * FROM telegram_channels ORDER BY name, chat_id"
            ).fetchall()
        else:
            rows = self._connection().execute(
                "SELECT * FROM profile_telegram_channels ORDER BY priority, title"
            ).fetchall()
        return [dict(row) for row in rows]

    def set_profile_channel(self, profile_id, account_id, channel):
        if self._uses_catalog():
            channel_ids = [] if channel is None else [channel["id"]]
            return self.set_profile_channels(profile_id, channel_ids)
        connection = self._connection()
        connection.execute(
            "DELETE FROM profile_telegram_channels WHERE profile_id=?", (profile_id,)
        )
        if channel is not None and account_id is not None:
            connection.execute(
                """
                INSERT INTO profile_telegram_channels
                (profile_id, account_id, chat_id, title, username, enabled, priority)
                VALUES (?, ?, ?, ?, ?, 1, 1)
                """,
                (
                    profile_id, account_id, channel["chat_id"],
                    channel.get("title", ""), channel.get("username", ""),
                ),
            )
        connection.commit()


profile_telegram_channel_repository = ProfileTelegramChannelRepository()
