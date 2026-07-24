"""Explicit and reversible Telegram channel catalog migration.

Imports and application startup never call this module automatically.
"""

LEGACY_TABLE = "profile_telegram_channels_legacy"


def _table_exists(connection, name):
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _columns(connection, table):
    return {row[1] for row in connection.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()}


def upgrade(connection):
    if _table_exists(connection, "telegram_channels"):
        return
    connection.execute("PRAGMA foreign_keys=OFF")
    try:
        connection.execute("BEGIN")
        legacy = (
            _table_exists(connection, "profile_telegram_channels")
            and "telegram_channel_id"
            not in _columns(connection, "profile_telegram_channels")
        )
        if legacy and not _table_exists(connection, LEGACY_TABLE):
            connection.execute(
                f"ALTER TABLE profile_telegram_channels RENAME TO {LEGACY_TABLE}"
            )
        connection.executescript(
            """
            CREATE TABLE telegram_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_account_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                username TEXT,
                chat_type TEXT NOT NULL DEFAULT 'UNKNOWN',
                can_read INTEGER NOT NULL DEFAULT 1,
                can_send INTEGER NOT NULL DEFAULT 0,
                enabled INTEGER NOT NULL DEFAULT 1,
                available INTEGER NOT NULL DEFAULT 1,
                last_synced_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(telegram_account_id) REFERENCES telegram_accounts(id)
                    ON DELETE CASCADE,
                UNIQUE(telegram_account_id, chat_id)
            );
            CREATE INDEX idx_telegram_channels_account
                ON telegram_channels(telegram_account_id);
            CREATE INDEX idx_telegram_channels_availability
                ON telegram_channels(telegram_account_id, available, enabled);
            CREATE TABLE IF NOT EXISTS profile_telegram_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                telegram_channel_id INTEGER NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                priority INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
                FOREIGN KEY(telegram_channel_id) REFERENCES telegram_channels(id)
                    ON DELETE CASCADE,
                UNIQUE(profile_id, telegram_channel_id)
            );
            CREATE INDEX idx_profile_telegram_channels_profile
                ON profile_telegram_channels(profile_id);
            CREATE INDEX idx_profile_telegram_channels_channel
                ON profile_telegram_channels(telegram_channel_id);
            """
        )
        if _table_exists(connection, LEGACY_TABLE):
            connection.execute(
                f"""
                INSERT OR IGNORE INTO telegram_channels (
                    telegram_account_id, chat_id, name, username,
                    chat_type, can_read, can_send, enabled, available
                )
                SELECT account_id, chat_id,
                    COALESCE(NULLIF(MAX(title), ''), CAST(chat_id AS TEXT)),
                    NULLIF(MAX(username), ''), 'UNKNOWN', 1, 0, MAX(enabled), 1
                FROM {LEGACY_TABLE}
                WHERE account_id IS NOT NULL AND chat_id IS NOT NULL
                GROUP BY account_id, chat_id
                """
            )
            connection.execute(
                f"""
                INSERT OR IGNORE INTO profile_telegram_channels (
                    profile_id, telegram_channel_id, enabled, priority
                )
                SELECT legacy.profile_id, channel.id,
                       legacy.enabled, legacy.priority
                FROM {LEGACY_TABLE} legacy
                JOIN telegram_channels channel
                  ON channel.telegram_account_id=legacy.account_id
                 AND channel.chat_id=legacy.chat_id
                WHERE legacy.profile_id IS NOT NULL
                """
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.execute("PRAGMA foreign_keys=ON")


def downgrade(connection):
    connection.execute("PRAGMA foreign_keys=OFF")
    try:
        connection.execute("BEGIN")
        connection.execute("DROP TABLE IF EXISTS profile_telegram_channels")
        connection.execute("DROP TABLE IF EXISTS telegram_channels")
        if _table_exists(connection, LEGACY_TABLE):
            connection.execute(
                f"ALTER TABLE {LEGACY_TABLE} RENAME TO profile_telegram_channels"
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.execute("PRAGMA foreign_keys=ON")
