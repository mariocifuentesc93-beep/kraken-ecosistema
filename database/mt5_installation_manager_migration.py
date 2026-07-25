"""Explicit, idempotent migration for the MT5 installation inventory.

Importing this module has no side effects. Production is upgraded only by an
operator calling :func:`upgrade` after a verified backup.
"""


_SETTINGS = {
    "internal.scanner.enabled": "0",
    "internal.scanner.mt5_terminal_id": "",
    "internal.scanner.output_directory": "",
    "internal.scanner.auto_start_terminal": "0",
}


def _columns(connection, table):
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def upgrade(connection):
    connection.execute("BEGIN")
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS mt5_terminals(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                broker TEXT NOT NULL DEFAULT '',
                executable_path TEXT NOT NULL,
                data_path TEXT NOT NULL DEFAULT '',
                catalog_id TEXT NOT NULL DEFAULT 'BRIDGE_SYNTHETICS',
                role TEXT NOT NULL DEFAULT 'TRADING'
                    CHECK(role IN ('TRADING','SCANNER')),
                active INTEGER NOT NULL DEFAULT 1,
                portable INTEGER NOT NULL DEFAULT 0,
                auto_start INTEGER NOT NULL DEFAULT 0,
                process_id INTEGER,
                connection_status TEXT NOT NULL DEFAULT 'STOPPED',
                last_seen_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(executable_path)
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_mt5_terminals_role_active "
            "ON mt5_terminals(role, active)"
        )
        if "mt5_terminal_id" not in _columns(connection, "mt5_accounts"):
            connection.execute(
                "ALTER TABLE mt5_accounts ADD COLUMN mt5_terminal_id INTEGER "
                "REFERENCES mt5_terminals(id)"
            )
        if "mt5_terminal_id" not in _columns(connection, "profiles"):
            connection.execute(
                "ALTER TABLE profiles ADD COLUMN mt5_terminal_id INTEGER "
                "REFERENCES mt5_terminals(id)"
            )
        if "catalog_id" not in _columns(connection, "profiles"):
            connection.execute(
                "ALTER TABLE profiles ADD COLUMN catalog_id TEXT "
                "NOT NULL DEFAULT 'BRIDGE_SYNTHETICS'"
            )
        for key, value in _SETTINGS.items():
            connection.execute(
                "INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",
                (key, value),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def downgrade(connection):
    connection.execute("BEGIN")
    try:
        for key in _SETTINGS:
            connection.execute("DELETE FROM settings WHERE key=?", (key,))
        # Supported by the SQLite version bundled with current Python.
        if "catalog_id" in _columns(connection, "profiles"):
            connection.execute("ALTER TABLE profiles DROP COLUMN catalog_id")
        if "mt5_terminal_id" in _columns(connection, "profiles"):
            connection.execute(
                "ALTER TABLE profiles DROP COLUMN mt5_terminal_id"
            )
        if "mt5_terminal_id" in _columns(connection, "mt5_accounts"):
            connection.execute(
                "ALTER TABLE mt5_accounts DROP COLUMN mt5_terminal_id"
            )
        connection.execute("DROP INDEX IF EXISTS idx_mt5_terminals_role_active")
        connection.execute("DROP TABLE IF EXISTS mt5_terminals")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
