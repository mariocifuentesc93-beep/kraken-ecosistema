"""Migración reversible de publicación INTERNAL hacia Telegram."""

import argparse
import sqlite3
from pathlib import Path


PROFILE_COLUMNS = (
    ("publish_internal_to_telegram", "INTEGER NOT NULL DEFAULT 0"),
    ("telegram_output_account_id", "INTEGER"),
    ("telegram_output_chat_id", "INTEGER"),
)


def _columns(connection, table):
    return {
        row[1]
        for row in connection.execute(f"PRAGMA table_info({table})")
    }


def _table_exists(connection, table):
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def upgrade(connection: sqlite3.Connection) -> bool:
    columns = _columns(connection, "profiles")
    changed = False
    try:
        connection.execute("BEGIN")
        for name, definition in PROFILE_COLUMNS:
            if name not in columns:
                connection.execute(
                    f"ALTER TABLE profiles ADD COLUMN {name} {definition}"
                )
                changed = True

        if not _table_exists(connection, "telegram_publications"):
            connection.execute(
                """
                CREATE TABLE telegram_publications(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id INTEGER NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    telegram_account_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    sent_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(signal_id) REFERENCES signals(id)
                        ON DELETE CASCADE,
                    FOREIGN KEY(telegram_account_id)
                        REFERENCES telegram_accounts(id) ON DELETE RESTRICT
                )
                """
            )
            changed = True
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_telegram_publication_destination
            ON telegram_publications(
                idempotency_key, telegram_account_id, chat_id
            )
            """
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return changed


def rollback(connection: sqlite3.Connection) -> bool:
    columns = _columns(connection, "profiles")
    names = [item[0] for item in PROFILE_COLUMNS]
    changed = (
        _table_exists(connection, "telegram_publications")
        or any(name in columns for name in names)
    )
    if not changed:
        return False
    try:
        connection.execute("BEGIN")
        connection.execute("DROP TABLE IF EXISTS telegram_publications")
        for name in reversed(names):
            if name in _columns(connection, "profiles"):
                connection.execute(
                    f"ALTER TABLE profiles DROP COLUMN {name}"
                )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Migra una base explícita para publicación INTERNAL."
    )
    parser.add_argument("action", choices=("upgrade", "rollback"))
    parser.add_argument("database", type=Path)
    arguments = parser.parse_args()
    connection = sqlite3.connect(arguments.database)
    try:
        changed = (
            upgrade(connection)
            if arguments.action == "upgrade"
            else rollback(connection)
        )
    finally:
        connection.close()
    print(f"{arguments.action}: {'applied' if changed else 'not-needed'}")


if __name__ == "__main__":
    main()
