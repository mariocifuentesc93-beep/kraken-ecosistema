import sqlite3
from pathlib import Path

from database.profile_trade_management_migration import (
    PROFILE_FLAGS,
    downgrade,
    upgrade,
)


def _columns(connection):
    return {
        row[1]
        for row in connection.execute("PRAGMA table_info(profiles)")
    }


def test_trade_management_migration_is_explicit_idempotent_and_reversible(
    tmp_path,
):
    database = tmp_path / "profile-management.db"
    connection = sqlite3.connect(database)
    connection.execute(
        "CREATE TABLE profiles (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
    )
    connection.execute("INSERT INTO profiles(name) VALUES('demo')")
    connection.commit()

    upgrade(connection)
    upgrade(connection)

    assert set(PROFILE_FLAGS) <= _columns(connection)
    row = connection.execute(
        """
        SELECT break_even_enabled, trailing_stop_enabled,
               partial_take_profit_enabled
        FROM profiles WHERE name='demo'
        """
    ).fetchone()
    assert row == (0, 0, 0)

    downgrade(connection)

    assert set(PROFILE_FLAGS).isdisjoint(_columns(connection))
    assert connection.execute(
        "SELECT name FROM profiles WHERE id=1"
    ).fetchone() == ("demo",)
    assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    connection.close()


def test_profile_repository_updates_terminal_account_and_trailing_flags(
    tmp_path,
):
    from database.database_manager import database_manager
    from database.mt5_installation_manager_migration import (
        upgrade as upgrade_mt5,
    )
    from models.profile import Profile
    from repositories.profile_repository import profile_repository

    original = database_manager.database
    database_manager.close()
    database_manager.database = Path(tmp_path) / "profile.db"
    try:
        database_manager.initialize()
        upgrade_mt5(database_manager.connect())
        database_manager.execute(
            """
            INSERT INTO mt5_terminals(id,name,executable_path)
            VALUES(8,'Bridge demo','C:/MT5 Demo/terminal64.exe')
            """
        )
        database_manager.execute(
            """
            INSERT INTO mt5_accounts(id,name,login,mt5_terminal_id)
            VALUES(3,'DEMO',243274,8)
            """
        )
        database_manager.commit()
        profile = profile_repository.create(Profile(name="demo"))

        profile.default_mt5_account = 3
        profile.mt5_terminal_id = 8
        profile.catalog_id = "BRIDGE_SYNTHETICS"
        profile.break_even_enabled = True
        profile.trailing_stop_enabled = True
        profile.partial_take_profit_enabled = True
        profile_repository.update(profile)

        database_manager.close()
        loaded = profile_repository.get_by_id(profile.id)
        assert loaded.default_mt5_account == 3
        assert loaded.mt5_terminal_id == 8
        assert loaded.catalog_id == "BRIDGE_SYNTHETICS"
        assert loaded.break_even_enabled is True
        assert loaded.trailing_stop_enabled is True
        assert loaded.partial_take_profit_enabled is True
    finally:
        database_manager.close()
        database_manager.database = original
