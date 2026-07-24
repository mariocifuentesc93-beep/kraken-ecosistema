"""Migración reversible del contrato persistente unificado de señales."""

import json
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path


MIGRATION_NAME = "001_unified_signal_contract"

NEW_COLUMNS = {
    "id",
    "source",
    "external_signal_id",
    "idempotency_key",
    "telegram_account_id",
    "chat_id",
    "message_id",
    "profile_id",
    "received_at",
    "detected_at",
    "symbol",
    "direction",
    "entry",
    "stop_loss",
    "take_profits",
    "raw_message",
    "metadata",
    "status",
    "score",
}


def _columns(connection, table_name):
    return {
        row[1]
        for row in connection.execute(f"PRAGMA table_info({table_name})")
    }


def _table_exists(connection, table_name):
    return connection.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (table_name,),
    ).fetchone() is not None


def _create_new_table(connection, table_name="signals"):
    connection.execute(
        f"""
        CREATE TABLE {table_name}(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL DEFAULT 'TELEGRAM',
            external_signal_id TEXT,
            idempotency_key TEXT NOT NULL,
            telegram_account_id INTEGER,
            chat_id INTEGER,
            message_id INTEGER,
            profile_id INTEGER,
            received_at TEXT NOT NULL,
            detected_at TEXT,
            symbol TEXT,
            direction TEXT,
            entry REAL,
            stop_loss REAL,
            take_profits TEXT NOT NULL DEFAULT '[]',
            raw_message TEXT,
            metadata TEXT NOT NULL DEFAULT '{{}}',
            status TEXT DEFAULT 'NEW',
            score REAL DEFAULT 0,
            FOREIGN KEY(profile_id)
                REFERENCES profiles(id)
                ON DELETE SET NULL
        )
        """
    )


def _create_legacy_table(connection, table_name="signals"):
    connection.execute(
        f"""
        CREATE TABLE {table_name}(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_account_id INTEGER,
            profile_id INTEGER,
            symbol TEXT,
            direction TEXT,
            entry REAL,
            stop_loss REAL,
            tp1 REAL,
            tp2 REAL,
            tp3 REAL,
            market_execution INTEGER DEFAULT 0,
            raw_message TEXT,
            status TEXT DEFAULT 'RECEIVED',
            created_at TEXT,
            FOREIGN KEY(profile_id)
                REFERENCES profiles(id)
                ON DELETE SET NULL
        )
        """
    )


def _replace_table(connection, source, destination):
    connection.execute("PRAGMA foreign_keys = OFF")
    try:
        connection.execute("BEGIN")
        connection.execute("DROP TABLE signals")
        connection.execute(f"ALTER TABLE {source} RENAME TO {destination}")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.execute("PRAGMA foreign_keys = ON")


def upgrade(connection: sqlite3.Connection) -> bool:
    """Actualiza ``signals``. Devuelve False si ya estaba actualizada."""
    if not _table_exists(connection, "signals"):
        _create_new_table(connection)
        connection.execute(
            """
            CREATE UNIQUE INDEX idx_signals_idempotency
            ON signals(idempotency_key)
            """
        )
        connection.commit()
        return True

    columns = _columns(connection, "signals")
    if NEW_COLUMNS.issubset(columns):
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_signals_idempotency
            ON signals(idempotency_key)
            """
        )
        connection.commit()
        return False

    _create_new_table(connection, "signals_unified")
    rows = connection.execute("SELECT * FROM signals ORDER BY id").fetchall()
    names = [item[0] for item in connection.execute(
        "SELECT name FROM pragma_table_info('signals')"
    )]

    for raw_row in rows:
        row = dict(zip(names, raw_row))
        take_profits = [
            row.get(name)
            for name in ("tp1", "tp2", "tp3")
            if row.get(name) is not None
        ]
        received_at = (
            row.get("received_at")
            or row.get("created_at")
            or datetime.now().isoformat(timespec="microseconds")
        )
        metadata = {}
        if "market_execution" in row:
            metadata["market_execution"] = bool(row.get("market_execution"))

        # Las filas heredadas carecen de chat_id/message_id. Su identidad
        # estable conserva el ID histórico sin inventar una identidad Telegram.
        idempotency_key = (
            row.get("idempotency_key")
            or f"LEGACY:{row.get('id')}"
        )
        connection.execute(
            """
            INSERT INTO signals_unified (
                id, source, external_signal_id, idempotency_key,
                telegram_account_id, chat_id, message_id, profile_id,
                received_at, detected_at, symbol, direction, entry,
                stop_loss, take_profits, raw_message, metadata,
                status, score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("id"),
                (row.get("source") or "TELEGRAM").upper(),
                row.get("external_signal_id"),
                idempotency_key,
                row.get("telegram_account_id"),
                row.get("chat_id"),
                row.get("message_id"),
                row.get("profile_id"),
                received_at,
                row.get("detected_at"),
                row.get("symbol"),
                row.get("direction"),
                row.get("entry"),
                row.get("stop_loss"),
                json.dumps(take_profits),
                row.get("raw_message"),
                json.dumps(metadata),
                row.get("status") or "RECEIVED",
                row.get("score") or 0.0,
            ),
        )

    connection.commit()
    _replace_table(connection, "signals_unified", "signals")
    connection.execute(
        """
        CREATE UNIQUE INDEX idx_signals_idempotency
        ON signals(idempotency_key)
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_signals_profile ON signals(profile_id)"
    )
    connection.commit()
    return True


def rollback(connection: sqlite3.Connection) -> bool:
    """Restaura el esquema previo y conserva los campos representables."""
    if not _table_exists(connection, "signals"):
        return False

    columns = _columns(connection, "signals")
    if "idempotency_key" not in columns:
        return False

    _create_legacy_table(connection, "signals_legacy")
    rows = connection.execute("SELECT * FROM signals ORDER BY id").fetchall()
    names = [item[0] for item in connection.execute(
        "SELECT name FROM pragma_table_info('signals')"
    )]

    for raw_row in rows:
        row = dict(zip(names, raw_row))
        take_profits = json.loads(row.get("take_profits") or "[]")
        metadata = json.loads(row.get("metadata") or "{}")
        padded = (take_profits + [None, None, None])[:3]
        connection.execute(
            """
            INSERT INTO signals_legacy (
                id, telegram_account_id, profile_id, symbol, direction,
                entry, stop_loss, tp1, tp2, tp3, market_execution,
                raw_message, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("id"),
                row.get("telegram_account_id"),
                row.get("profile_id"),
                row.get("symbol"),
                row.get("direction"),
                row.get("entry"),
                row.get("stop_loss"),
                padded[0],
                padded[1],
                padded[2],
                int(bool(metadata.get("market_execution", False))),
                row.get("raw_message"),
                row.get("status"),
                row.get("received_at"),
            ),
        )

    connection.commit()
    _replace_table(connection, "signals_legacy", "signals")
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_signals_profile ON signals(profile_id)"
    )
    connection.commit()
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Migra explícitamente una base SQLite del contrato Signal."
    )
    parser.add_argument("action", choices=("upgrade", "rollback"))
    parser.add_argument(
        "database",
        type=Path,
        help="Ruta explícita de la base. No existe un valor por defecto.",
    )
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
