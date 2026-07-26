"""Explicit, idempotent profile risk migration. Importing is read-only."""


def _columns(connection):
    return {row[1] for row in connection.execute("PRAGMA table_info(profiles)")}


def upgrade(connection):
    connection.execute("BEGIN")
    try:
        if "max_risk_percent" not in _columns(connection):
            connection.execute(
                "ALTER TABLE profiles ADD COLUMN max_risk_percent REAL DEFAULT 5.0"
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def downgrade(connection):
    connection.execute("BEGIN")
    try:
        if "max_risk_percent" in _columns(connection):
            connection.execute(
                "ALTER TABLE profiles DROP COLUMN max_risk_percent"
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
