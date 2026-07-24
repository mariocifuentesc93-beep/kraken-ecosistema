import sqlite3

from database.schema import create_tables
from database.telegram_publication_migration import rollback, upgrade


def legacy_database(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE profiles(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            operation_mode TEXT DEFAULT 'telegram',
            publish_internal_to_telegram INTEGER NOT NULL DEFAULT 0,
            telegram_output_account_id INTEGER,
            telegram_output_chat_id INTEGER
        );
        CREATE TABLE settings(
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE signals(
            id INTEGER PRIMARY KEY,
            idempotency_key TEXT NOT NULL UNIQUE
        );
        CREATE TABLE telegram_accounts(
            id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 1
        );
        INSERT INTO profiles(
            id,
            name,
            publish_internal_to_telegram,
            telegram_output_account_id,
            telegram_output_chat_id
        ) VALUES (1, 'Existing', 0, NULL, NULL);
        INSERT INTO settings(key, value)
        VALUES ('execution_mode', 'OFF');
        """
    )
    connection.commit()
    return connection


def test_migration_adds_global_configuration_without_copying_legacy(tmp_path):
    connection = legacy_database(tmp_path / "publication.db")

    assert upgrade(connection) is True

    profile_columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(profiles)")
    }
    assert "publish_internal_to_telegram" in profile_columns
    assert "telegram_output_account_id" in profile_columns
    assert "telegram_output_chat_id" in profile_columns
    indexes = connection.execute(
        "PRAGMA index_list(telegram_publications)"
    ).fetchall()
    assert any(item[2] == 1 for item in indexes)
    assert connection.execute(
        "SELECT name FROM profiles WHERE id=1"
    ).fetchone()[0] == "Existing"
    settings = dict(
        connection.execute(
            """
            SELECT key, value FROM settings
            WHERE key LIKE 'internal.telegram_publication.%'
            """
        ).fetchall()
    )
    assert settings == {
        "internal.telegram_publication.enabled": "0",
    }
    connection.close()


def test_migration_rollback_removes_global_configuration_and_table(tmp_path):
    connection = legacy_database(tmp_path / "rollback.db")
    upgrade(connection)

    assert rollback(connection) is True

    assert connection.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type='table' AND name='telegram_publications'
        """
    ).fetchone() is None
    assert connection.execute(
        "SELECT name FROM profiles WHERE id=1"
    ).fetchone()[0] == "Existing"
    assert connection.execute(
        """
        SELECT COUNT(*) FROM settings
        WHERE key LIKE 'internal.telegram_publication.%'
        """
    ).fetchone()[0] == 0
    assert connection.execute(
        "SELECT value FROM settings WHERE key='execution_mode'"
    ).fetchone()[0] == "OFF"
    connection.close()


def test_fresh_schema_has_no_profile_publication_fields():
    connection = sqlite3.connect(":memory:")
    create_tables(connection)
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(profiles)")
    }
    assert "publish_internal_to_telegram" not in columns
    assert "telegram_output_account_id" not in columns
    assert "telegram_output_chat_id" not in columns
    assert connection.execute(
        """
        SELECT value FROM settings
        WHERE key='internal.telegram_publication.enabled'
        """
    ).fetchone()[0] == "0"
    connection.close()
