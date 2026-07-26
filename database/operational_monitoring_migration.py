"""Explicit persistence for operational observability.

Importing this module has no side effects.  ``upgrade`` and ``downgrade`` must
be called explicitly by the application's migration lifecycle.
"""

from __future__ import annotations


SETTINGS = {
    "monitoring.refresh_interval_seconds": "5",
    "internal.scanner.stale_after_minutes": "30",
}


def upgrade(connection):
    with connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS operational_events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,
                external_signal_id TEXT,
                source TEXT,
                profile_id INTEGER,
                operation_id INTEGER,
                telegram_publication_id INTEGER,
                terminal_id INTEGER,
                account_id INTEGER,
                timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                stage TEXT NOT NULL,
                status TEXT NOT NULL,
                reason TEXT,
                duration_ms INTEGER,
                metadata TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY(signal_id) REFERENCES signals(id) ON DELETE SET NULL,
                FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE SET NULL,
                FOREIGN KEY(operation_id) REFERENCES operations(id) ON DELETE SET NULL
            );
            CREATE INDEX IF NOT EXISTS idx_operational_events_signal
                ON operational_events(signal_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_operational_events_stage
                ON operational_events(stage, status, timestamp);

            CREATE TABLE IF NOT EXISTS operational_alerts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint TEXT NOT NULL UNIQUE,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'ACTIVE',
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                occurrence_count INTEGER NOT NULL DEFAULT 1,
                component TEXT NOT NULL,
                message TEXT NOT NULL,
                recommended_action TEXT,
                resolved_at TEXT,
                metadata TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_operational_alerts_state
                ON operational_alerts(state, severity, last_seen_at);
            """
        )
        for key, value in SETTINGS.items():
            connection.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
                (key, value),
            )


def downgrade(connection):
    with connection:
        connection.execute("DROP TABLE IF EXISTS operational_alerts")
        connection.execute("DROP TABLE IF EXISTS operational_events")
        for key in SETTINGS:
            connection.execute("DELETE FROM settings WHERE key=?", (key,))
