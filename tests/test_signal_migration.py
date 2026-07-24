import sqlite3

from database.signal_contract_migration import rollback, upgrade
from models.signal import Signal
from repositories.signal_repository import SignalRepository


def _legacy_database(path):
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE profiles(
            id INTEGER PRIMARY KEY AUTOINCREMENT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE signals(
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
            created_at TEXT
        )
        """
    )
    connection.execute(
        """
        INSERT INTO signals(
            telegram_account_id, symbol, direction, entry, stop_loss,
            tp1, tp2, tp3, market_execution, raw_message, status, created_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            7,
            "EmasVol20",
            "BUY",
            100,
            90,
            110,
            120,
            130,
            1,
            "legacy",
            "RECEIVED",
            "2026-07-23 10:00:00",
        ),
    )
    connection.commit()
    return connection


def test_migration_preserves_existing_signal(tmp_path):
    connection = _legacy_database(tmp_path / "migration.db")

    assert upgrade(connection) is True
    row = connection.execute("SELECT * FROM signals").fetchone()
    columns = [
        item[1]
        for item in connection.execute("PRAGMA table_info(signals)")
    ]
    data = dict(zip(columns, row))

    assert data["id"] == 1
    assert data["source"] == "TELEGRAM"
    assert data["idempotency_key"] == "LEGACY:1"
    assert data["take_profits"] == "[110.0, 120.0, 130.0]"
    assert data["received_at"] == "2026-07-23 10:00:00"
    indexes = {
        item[1]: item[2]
        for item in connection.execute("PRAGMA index_list(signals)")
    }
    assert indexes["idx_signals_idempotency"] == 1
    assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_migration_rollback_restores_legacy_schema(tmp_path):
    connection = _legacy_database(tmp_path / "rollback.db")
    upgrade(connection)

    assert rollback(connection) is True
    columns = {
        item[1]
        for item in connection.execute("PRAGMA table_info(signals)")
    }
    row = connection.execute(
        "SELECT tp1, tp2, tp3, market_execution, created_at FROM signals"
    ).fetchone()

    assert "idempotency_key" not in columns
    assert {"tp1", "tp2", "tp3", "market_execution", "created_at"} <= columns
    assert row == (110.0, 120.0, 130.0, 1, "2026-07-23 10:00:00")


def test_rollback_starting_from_new_schema(tmp_path):
    connection = sqlite3.connect(tmp_path / "new-schema.db")
    connection.row_factory = sqlite3.Row
    upgrade(connection)
    SignalRepository(connection).create(
        Signal(
            source="INTERNAL",
            external_signal_id="12241",
            symbol="LionX75",
            take_profits=[110, 120, 130],
            metadata={"market_execution": True},
        )
    )

    assert rollback(connection) is True
    columns = {
        item[1]
        for item in connection.execute("PRAGMA table_info(signals)")
    }
    row = connection.execute(
        "SELECT tp1, tp2, tp3, market_execution FROM signals"
    ).fetchone()

    assert "idempotency_key" not in columns
    assert {"tp1", "tp2", "tp3", "created_at"} <= columns
    assert tuple(row) == (110.0, 120.0, 130.0, 1)
