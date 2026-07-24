"""Explicit cleanup for retiring all local Telegram configuration.

This module has no import-time side effects.  Call ``clear_telegram_configuration``
with an existing SQLite connection, then remove local session/config files with
``remove_local_telegram_files``.
"""

from pathlib import Path


TELEGRAM_TABLES_IN_DELETE_ORDER = (
    "telegram_channel_validations",
    "telegram_diagnostics",
    "telegram_publications",
    "profile_telegram_channels",
    "telegram_accounts",
)

LEGACY_PROFILE_VALUES = {
    "telegram_account_id": None,
    "telegram_channel_id": None,
    "publish_internal_to_telegram": 0,
    "telegram_output_account_id": None,
    "telegram_output_chat_id": None,
}


def _table_exists(connection, table_name):
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone() is not None


def _table_columns(connection, table_name):
    if not _table_exists(connection, table_name):
        return set()
    return {
        row[1]
        for row in connection.execute(f'PRAGMA table_info("{table_name}")')
    }


def clear_telegram_configuration(connection):
    """Remove Telegram data in one transaction without changing the schema."""

    counts = {}
    with connection:
        for table_name in TELEGRAM_TABLES_IN_DELETE_ORDER:
            if not _table_exists(connection, table_name):
                counts[table_name] = 0
                continue
            counts[table_name] = connection.execute(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).fetchone()[0]
            connection.execute(f'DELETE FROM "{table_name}"')

        profile_columns = _table_columns(connection, "profiles")
        assignments = [
            (column, value)
            for column, value in LEGACY_PROFILE_VALUES.items()
            if column in profile_columns
        ]
        if assignments:
            sql = ", ".join(f'"{column}"=?' for column, _ in assignments)
            connection.execute(
                f'UPDATE "profiles" SET {sql}',
                tuple(value for _, value in assignments),
            )

        if _table_exists(connection, "settings"):
            counts["settings"] = connection.execute(
                """
                SELECT COUNT(*) FROM settings
                WHERE lower(key) LIKE '%telegram%'
                   OR lower(key) LIKE '%telethon%'
                   OR lower(key) LIKE '%chat_id%'
                   OR lower(key) LIKE '%session%'
                """
            ).fetchone()[0]
            connection.execute(
                """
                DELETE FROM settings
                WHERE lower(key) LIKE '%telegram%'
                   OR lower(key) LIKE '%telethon%'
                   OR lower(key) LIKE '%chat_id%'
                   OR lower(key) LIKE '%session%'
                """
            )

        if _table_exists(connection, "sqlite_sequence"):
            placeholders = ",".join("?" for _ in TELEGRAM_TABLES_IN_DELETE_ORDER)
            connection.execute(
                f"DELETE FROM sqlite_sequence WHERE name IN ({placeholders})",
                TELEGRAM_TABLES_IN_DELETE_ORDER,
            )

    return counts


def remove_local_telegram_files(session_directory, legacy_config_path=None):
    """Delete Telethon session artifacts and the retired local config file."""

    removed = []
    session_path = Path(session_directory)
    if session_path.is_dir():
        for candidate in session_path.glob("*.session*"):
            if candidate.is_file():
                candidate.unlink()
                removed.append(candidate)

    if legacy_config_path is not None:
        config_path = Path(legacy_config_path)
        if config_path.is_file():
            config_path.unlink()
            removed.append(config_path)

    return removed
