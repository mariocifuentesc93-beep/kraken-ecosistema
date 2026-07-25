"""Explicit, idempotent and reversible Weltrade catalog migration.

This module is intentionally not imported by application startup. The fixed
catalog is visible from code; this migration persists its 25 definitions only
when an operator explicitly invokes :func:`upgrade`.
"""

from config.symbols import WELTRADE_CATALOG, get_symbol_catalog


def upgrade(connection):
    connection.execute("BEGIN")
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS symbol_catalog(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                canonical_name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                mt5_symbol TEXT NOT NULL,
                catalog TEXT NOT NULL,
                broker TEXT NOT NULL,
                category TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0,
                availability TEXT NOT NULL DEFAULT 'NOT_VERIFIED',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(catalog, canonical_name)
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_symbol_catalog_grouping
            ON symbol_catalog(catalog, category, sort_order)
            """
        )
        for item in get_symbol_catalog(WELTRADE_CATALOG):
            connection.execute(
                """
                INSERT INTO symbol_catalog(
                    canonical_name, display_name, mt5_symbol, catalog, broker,
                    category, enabled, sort_order, availability
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'NOT_VERIFIED')
                ON CONFLICT(catalog, canonical_name) DO UPDATE SET
                    display_name=excluded.display_name,
                    mt5_symbol=excluded.mt5_symbol,
                    catalog=excluded.catalog,
                    broker=excluded.broker,
                    category=excluded.category,
                    sort_order=excluded.sort_order
                """,
                (
                    item["canonical_name"],
                    item["display_name"],
                    item["mt5_symbol"],
                    item["catalog"],
                    item["broker"],
                    item["category"],
                    int(item["enabled"]),
                    item["sort_order"],
                ),
            )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS profile_symbol_catalog_context(
                symbol_id INTEGER PRIMARY KEY,
                profile_id INTEGER NOT NULL,
                catalog_id TEXT NOT NULL,
                canonical_name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(symbol_id) REFERENCES symbols(id) ON DELETE CASCADE,
                FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
                UNIQUE(profile_id, catalog_id, canonical_name)
            )
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO profile_symbol_catalog_context(
                symbol_id, profile_id, catalog_id, canonical_name
            )
            SELECT id, profile_id, 'BRIDGE_SYNTHETICS', UPPER(symbol)
            FROM symbols
            """
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def downgrade(connection):
    connection.execute("BEGIN")
    try:
        if connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='symbol_catalog'"
        ).fetchone():
            connection.execute(
                "DELETE FROM symbol_catalog WHERE catalog=?",
                (WELTRADE_CATALOG,),
            )
        connection.execute(
            "DROP TABLE IF EXISTS profile_symbol_catalog_context"
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
