"""Explicit profile trade-management migration. Importing is read-only."""


PROFILE_FLAGS = {
    "break_even_enabled": "INTEGER NOT NULL DEFAULT 0",
    "trailing_stop_enabled": "INTEGER NOT NULL DEFAULT 0",
    "partial_take_profit_enabled": "INTEGER NOT NULL DEFAULT 0",
}


def _columns(connection):
    return {
        row[1]
        for row in connection.execute("PRAGMA table_info(profiles)")
    }


def upgrade(connection):
    connection.execute("BEGIN")
    try:
        columns = _columns(connection)
        for name, definition in PROFILE_FLAGS.items():
            if name not in columns:
                connection.execute(
                    f"ALTER TABLE profiles ADD COLUMN {name} {definition}"
                )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def downgrade(connection):
    connection.execute("BEGIN")
    try:
        columns = _columns(connection)
        for name in reversed(tuple(PROFILE_FLAGS)):
            if name in columns:
                connection.execute(
                    f"ALTER TABLE profiles DROP COLUMN {name}"
                )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
