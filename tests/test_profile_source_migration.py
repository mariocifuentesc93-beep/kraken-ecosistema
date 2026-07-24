import sqlite3

from database.profile_source_migration import rollback, upgrade


def legacy_database(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE profiles(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            operation_mode TEXT DEFAULT 'telegram',
            execution_mode TEXT DEFAULT 'LIVE'
        )
        """
    )
    connection.executemany(
        """
        INSERT INTO profiles(id, name, operation_mode, execution_mode)
        VALUES (?, ?, ?, ?)
        """,
        [
            (1, "Telegram", "telegram", "SIMULATION"),
            (2, "Both", "both", "OFF"),
            (3, "Manual", "manual", "LIVE"),
        ],
    )
    connection.commit()
    return connection


def columns(connection):
    return {
        row[1]
        for row in connection.execute("PRAGMA table_info(profiles)")
    }


def test_profile_source_migration_preserves_and_maps_profiles(tmp_path):
    connection = legacy_database(tmp_path / "profiles.db")

    assert upgrade(connection) is True
    rows = connection.execute(
        """
        SELECT id, name, operation_mode, execution_mode, signal_source_mode
        FROM profiles ORDER BY id
        """
    ).fetchall()

    assert [tuple(row) for row in rows] == [
        (1, "Telegram", "telegram", "SIMULATION", "TELEGRAM"),
        (2, "Both", "both", "OFF", "BOTH"),
        (3, "Manual", "manual", "LIVE", "OFF"),
    ]
    assert upgrade(connection) is False
    connection.close()


def test_profile_source_migration_rollback(tmp_path):
    connection = legacy_database(tmp_path / "rollback.db")
    upgrade(connection)

    assert rollback(connection) is True
    assert "signal_source_mode" not in columns(connection)
    assert connection.execute(
        "SELECT COUNT(*) FROM profiles"
    ).fetchone()[0] == 3
    assert rollback(connection) is False
    connection.close()
