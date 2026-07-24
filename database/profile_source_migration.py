"""Migración reversible de selección de fuente automática por perfil."""

import argparse
import sqlite3
from pathlib import Path


COLUMN = "signal_source_mode"


def _columns(connection):
    return {
        row[1]
        for row in connection.execute("PRAGMA table_info(profiles)")
    }


def upgrade(connection: sqlite3.Connection) -> bool:
    if COLUMN in _columns(connection):
        return False

    try:
        connection.execute("BEGIN")
        connection.execute(
            "ALTER TABLE profiles ADD COLUMN signal_source_mode TEXT"
        )
        connection.execute(
            """
            UPDATE profiles
            SET signal_source_mode = CASE LOWER(TRIM(operation_mode))
                WHEN 'telegram' THEN 'TELEGRAM'
                WHEN 'both' THEN 'BOTH'
                WHEN 'manual' THEN 'OFF'
                ELSE 'OFF'
            END
            """
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return True


def rollback(connection: sqlite3.Connection) -> bool:
    if COLUMN not in _columns(connection):
        return False

    try:
        connection.execute("BEGIN")
        connection.execute(
            "ALTER TABLE profiles DROP COLUMN signal_source_mode"
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Migra una base explícita para signal_source_mode."
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
