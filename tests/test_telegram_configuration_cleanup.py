import sqlite3

from utils.telegram_configuration_cleanup import (
    clear_telegram_configuration,
    remove_local_telegram_files,
)


def _database():
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        PRAGMA foreign_keys=ON;
        CREATE TABLE profiles(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            risk_percent REAL,
            telegram_account_id INTEGER,
            telegram_channel_id INTEGER,
            publish_internal_to_telegram INTEGER,
            telegram_output_account_id INTEGER,
            telegram_output_chat_id INTEGER
        );
        CREATE TABLE telegram_accounts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            api_id INTEGER,
            api_hash TEXT,
            session_name TEXT,
            username TEXT
        );
        CREATE TABLE profile_telegram_channels(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER,
            account_id INTEGER,
            chat_id INTEGER,
            username TEXT
        );
        CREATE TABLE telegram_publications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_account_id INTEGER,
            chat_id INTEGER
        );
        CREATE TABLE telegram_diagnostics(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER
        );
        CREATE TABLE telegram_channel_validations(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            diagnostic_id INTEGER,
            chat_id INTEGER
        );
        CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE symbols(id INTEGER PRIMARY KEY, symbol TEXT);
        CREATE TABLE mt5_accounts(id INTEGER PRIMARY KEY, login INTEGER);

        INSERT INTO profiles VALUES
            (1, 'Principal', 1.5, 7, 8, 1, 7, -100123);
        INSERT INTO telegram_accounts
            (id, phone, api_id, api_hash, session_name, username)
            VALUES (7, '+000', 123, 'secret', 'old', 'old_user');
        INSERT INTO profile_telegram_channels
            (profile_id, account_id, chat_id, username)
            VALUES (1, 7, -100123, 'old_channel');
        INSERT INTO telegram_publications
            (telegram_account_id, chat_id) VALUES (7, -100123);
        INSERT INTO telegram_diagnostics(account_id) VALUES (7);
        INSERT INTO telegram_channel_validations(diagnostic_id, chat_id)
            VALUES (1, -100123);
        INSERT INTO settings VALUES
            ('internal.telegram_publication.enabled', '1'),
            ('internal.telegram_publication.chat_id', '-100123'),
            ('execution_mode', 'OFF');
        INSERT INTO symbols VALUES (1, 'EURUSD');
        INSERT INTO mt5_accounts VALUES (1, 900001);
        """
    )
    return connection


def test_cleanup_removes_only_telegram_configuration():
    connection = _database()

    counts = clear_telegram_configuration(connection)

    assert counts["telegram_accounts"] == 1
    for table in (
        "telegram_accounts",
        "profile_telegram_channels",
        "telegram_publications",
        "telegram_diagnostics",
        "telegram_channel_validations",
    ):
        assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0

    profile = connection.execute("SELECT * FROM profiles").fetchone()
    assert profile[1] == "Principal"
    assert profile[2] == 1.5
    assert profile[3:] == (None, None, 0, None, None)
    assert connection.execute("SELECT COUNT(*) FROM symbols").fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM mt5_accounts").fetchone()[0] == 1
    assert connection.execute(
        "SELECT value FROM settings WHERE key='execution_mode'"
    ).fetchone()[0] == "OFF"
    assert connection.execute(
        "SELECT COUNT(*) FROM settings WHERE key LIKE '%telegram%'"
    ).fetchone()[0] == 0


def test_cleanup_is_idempotent():
    connection = _database()

    clear_telegram_configuration(connection)
    second = clear_telegram_configuration(connection)

    assert all(value == 0 for value in second.values())
    assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_local_session_and_legacy_config_are_removed(tmp_path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    session = sessions / "old.session"
    journal = sessions / "old.session-journal"
    unrelated = sessions / "keep.txt"
    config = tmp_path / "config.yaml"
    for path in (session, journal, unrelated, config):
        path.write_text("test", encoding="utf-8")

    removed = remove_local_telegram_files(sessions, config)

    assert set(removed) == {session, journal, config}
    assert unrelated.exists()
    assert not session.exists()
    assert not journal.exists()
    assert not config.exists()
