"""Explicit migration for independent MT5 terminal capabilities and states.

Importing this module never changes a database. Operators must call
``upgrade(connection)`` after creating and verifying a backup.

The legacy ``role`` column remains available during the compatibility period:

* ``TRADING`` maps to ``can_trade=1, can_scan=0``.
* ``SCANNER`` maps to ``can_trade=0, can_scan=1``.

After migration a terminal may safely expose both capabilities.
"""


_CAPABILITY_COLUMNS = (
    ("can_trade", "INTEGER NOT NULL DEFAULT 0 CHECK(can_trade IN (0,1))"),
    ("can_scan", "INTEGER NOT NULL DEFAULT 0 CHECK(can_scan IN (0,1))"),
    ("process_status", "TEXT NOT NULL DEFAULT 'STOPPED'"),
    (
        "trading_connection_status",
        "TEXT NOT NULL DEFAULT 'NOT_VALIDATED'",
    ),
    ("scanner_status", "TEXT NOT NULL DEFAULT 'INACTIVE'"),
    ("account_match_status", "TEXT NOT NULL DEFAULT 'NOT_VALIDATED'"),
    ("detected_login", "TEXT"),
    ("detected_server", "TEXT"),
)


def _columns(connection, table):
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def upgrade(connection):
    connection.execute("BEGIN")
    try:
        columns = _columns(connection, "mt5_terminals")
        migrate_legacy_roles = (
            "can_trade" not in columns or "can_scan" not in columns
        )
        for name, definition in _CAPABILITY_COLUMNS:
            if name not in columns:
                connection.execute(
                    f"ALTER TABLE mt5_terminals ADD COLUMN {name} {definition}"
                )
                columns.add(name)

        if migrate_legacy_roles:
            connection.execute(
                """
                UPDATE mt5_terminals
                SET can_trade=CASE
                        WHEN UPPER(role)='TRADING' THEN 1 ELSE 0 END,
                    can_scan=CASE
                        WHEN UPPER(role)='SCANNER' THEN 1 ELSE 0 END
                """
            )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_mt5_terminals_capabilities_active
            ON mt5_terminals(can_trade, can_scan, active)
            """
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def downgrade(connection):
    connection.execute("BEGIN")
    try:
        connection.execute(
            "DROP INDEX IF EXISTS idx_mt5_terminals_capabilities_active"
        )
        columns = _columns(connection, "mt5_terminals")
        for name, _definition in reversed(_CAPABILITY_COLUMNS):
            if name in columns:
                connection.execute(
                    f"ALTER TABLE mt5_terminals DROP COLUMN {name}"
                )
                columns.remove(name)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
