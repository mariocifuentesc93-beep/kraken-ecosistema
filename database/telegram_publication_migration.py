"""Schema migration for global INTERNAL Telegram publication reservations."""

import argparse
import sqlite3
from pathlib import Path


def _table_exists(connection, table):
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        is not None
    )


def upgrade(connection: sqlite3.Connection) -> bool:
    changed = False
    with connection:
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
                    FOREIGN KEY(signal_id)
                        REFERENCES signals(id) ON DELETE CASCADE,
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
                idempotency_key,
                telegram_account_id,
                chat_id
            )
            """
        )
    return changed


def rollback(connection: sqlite3.Connection) -> bool:
    if not _table_exists(connection, "telegram_publications"):
        return False
    with connection:
        connection.execute("DROP TABLE telegram_publications")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("--rollback", action="store_true")
    arguments = parser.parse_args(argv)
    connection = sqlite3.connect(arguments.database)
    try:
        changed = (
            rollback(connection)
            if arguments.rollback
            else upgrade(connection)
        )
        print("changed" if changed else "unchanged")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
