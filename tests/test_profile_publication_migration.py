import sqlite3

from database.internal_telegram_publication_migration import (
    rollback,
    upgrade,
)
from database.schema import create_tables


def legacy_database(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE profiles(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            operation_mode TEXT DEFAULT 'telegram'
        );
        CREATE TABLE signals(
            id INTEGER PRIMARY KEY,
            idempotency_key TEXT NOT NULL UNIQUE
        );
        CREATE TABLE telegram_accounts(
            id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 1
        );
        INSERT INTO profiles(id, name) VALUES (1, 'Existing');
        """
    )
    connection.commit()
    return connection


def test_migration_preserves_profiles_and_safe_defaults(tmp_path):
    connection = legacy_database(tmp_path / "profile-publication.db")
    assert upgrade(connection) is True
    row = connection.execute(
        "SELECT * FROM profiles WHERE id=1"
    ).fetchone()
    assert row["name"] == "Existing"
    assert row["publish_internal_to_telegram"] == 0
    assert row["telegram_output_account_id"] is None
    assert row["telegram_output_chat_id"] is None
    indexes = connection.execute(
        "PRAGMA index_list(telegram_publications)"
    ).fetchall()
    assert any(item[2] == 1 for item in indexes)
    connection.close()


def test_migration_rollback_removes_only_phase_five_schema(tmp_path):
    connection = legacy_database(tmp_path / "profile-rollback.db")
    upgrade(connection)
    assert rollback(connection) is True
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(profiles)")
    }
    assert "publish_internal_to_telegram" not in columns
    assert connection.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type='table' AND name='telegram_publications'
        """
    ).fetchone() is None
    assert connection.execute(
        "SELECT name FROM profiles WHERE id=1"
    ).fetchone()[0] == "Existing"
    connection.close()


def test_rollback_starts_from_fresh_phase_five_schema():
    connection = sqlite3.connect(":memory:")
    create_tables(connection)
    connection.execute(
        "INSERT INTO profiles(name) VALUES ('Fresh profile')"
    )
    connection.commit()
    assert rollback(connection) is True
    assert connection.execute(
        "SELECT name FROM profiles"
    ).fetchone()[0] == "Fresh profile"
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(profiles)")
    }
    assert "publish_internal_to_telegram" not in columns
    connection.close()
