import asyncio
import sqlite3
from types import SimpleNamespace

import pytest

from database.telegram_channel_catalog_migration import downgrade, upgrade
from database.schema import create_tables
from repositories.profile_telegram_repository import (
    ProfileTelegramChannelRepository,
)
from repositories.telegram_channel_repository import TelegramChannelRepository
from services.telegram_channel_sync_service import TelegramChannelSyncService


def connection():
    value = sqlite3.connect(":memory:")
    value.row_factory = sqlite3.Row
    value.execute("PRAGMA foreign_keys=ON")
    value.executescript(
        """
        CREATE TABLE telegram_accounts (
            id INTEGER PRIMARY KEY, name TEXT, authorized INTEGER, enabled INTEGER
        );
        CREATE TABLE profiles (
            id INTEGER PRIMARY KEY, name TEXT, enabled INTEGER DEFAULT 1,
            signal_source_mode TEXT DEFAULT 'TELEGRAM'
        );
        CREATE TABLE profile_telegram_channels (
            id INTEGER PRIMARY KEY,
            profile_id INTEGER,
            account_id INTEGER,
            chat_id INTEGER,
            title TEXT,
            username TEXT,
            enabled INTEGER DEFAULT 1,
            priority INTEGER DEFAULT 1
        );
        """
    )
    return value


def dialogs():
    return [
        {
            "chat_id": -1001,
            "name": "Canal público",
            "username": "premium",
            "chat_type": "CANAL",
            "can_read": True,
            "can_send": False,
        },
        {
            "chat_id": -1002,
            "name": "Canal privado",
            "username": None,
            "chat_type": "CANAL",
            "can_read": True,
            "can_send": True,
        },
        {
            "chat_id": -1003,
            "name": "Grupo",
            "username": None,
            "chat_type": "GRUPO",
            "can_read": True,
            "can_send": True,
        },
        {
            "chat_id": -1004,
            "name": "Supergrupo",
            "username": "vip",
            "chat_type": "SUPERGRUPO",
            "can_read": True,
            "can_send": True,
        },
    ]


def test_migration_preserves_legacy_associations_and_is_reversible():
    db = connection()
    db.execute("INSERT INTO telegram_accounts VALUES (7, 'Cuenta', 1, 1)")
    db.execute("INSERT INTO profiles VALUES (1, 'A', 1, 'TELEGRAM')")
    db.execute(
        """
        INSERT INTO profile_telegram_channels
        (id, profile_id, account_id, chat_id, title, username, enabled, priority)
        VALUES (1, 1, 7, -1001, 'Premium', 'premium', 1, 2)
        """
    )
    db.commit()

    upgrade(db)

    channel = db.execute("SELECT * FROM telegram_channels").fetchone()
    relation = db.execute("SELECT * FROM profile_telegram_channels").fetchone()
    assert channel["telegram_account_id"] == 7
    assert channel["chat_id"] == -1001
    assert relation["profile_id"] == 1
    assert relation["telegram_channel_id"] == channel["id"]

    downgrade(db)
    columns = {
        row[1]
        for row in db.execute(
            "PRAGMA table_info(profile_telegram_channels)"
        ).fetchall()
    }
    assert {"account_id", "chat_id", "title"} <= columns
    assert db.execute(
        "SELECT COUNT(*) FROM profile_telegram_channels"
    ).fetchone()[0] == 1


def test_catalog_sync_supports_all_chat_types_and_null_username():
    db = connection()
    db.execute("INSERT INTO telegram_accounts VALUES (7, 'Cuenta', 1, 1)")
    db.commit()
    upgrade(db)
    repository = TelegramChannelRepository(db)

    result = repository.synchronize(7, dialogs(), "2026-07-24 10:00:00")

    assert len(result) == 4
    assert {item.chat_type for item in result} == {
        "CANAL", "GRUPO", "SUPERGRUPO"
    }
    assert repository.get_by_identity(7, -1002).username is None
    assert len(repository.list_sendable(7)) == 3


def test_repeated_sync_does_not_duplicate_and_marks_missing_unavailable():
    db = connection()
    db.execute("INSERT INTO telegram_accounts VALUES (7, 'Cuenta', 1, 1)")
    db.commit()
    upgrade(db)
    repository = TelegramChannelRepository(db)
    repository.synchronize(7, dialogs())
    repository.synchronize(7, dialogs()[:1])

    assert db.execute("SELECT COUNT(*) FROM telegram_channels").fetchone()[0] == 4
    assert repository.get_by_identity(7, -1001).available is True
    assert repository.get_by_identity(7, -1002).available is False


def test_same_chat_id_in_two_accounts_has_independent_identity():
    db = connection()
    db.executemany(
        "INSERT INTO telegram_accounts VALUES (?, ?, 1, 1)",
        [(7, "A"), (8, "B")],
    )
    db.commit()
    upgrade(db)
    repository = TelegramChannelRepository(db)
    repository.synchronize(7, [dialogs()[0]])
    repository.synchronize(8, [dialogs()[0]])

    assert db.execute("SELECT COUNT(*) FROM telegram_channels").fetchone()[0] == 2


def test_profiles_select_many_and_share_channel_without_cross_deletion():
    db = connection()
    db.execute("INSERT INTO telegram_accounts VALUES (7, 'Cuenta', 1, 1)")
    db.executemany(
        "INSERT INTO profiles VALUES (?, ?, 1, 'TELEGRAM')",
        [(1, "A"), (2, "B")],
    )
    db.commit()
    upgrade(db)
    channels = TelegramChannelRepository(db)
    channels.synchronize(7, dialogs()[:2])
    ids = [item.id for item in channels.list_by_account(7)]
    relations = ProfileTelegramChannelRepository(db)

    relations.set_profile_channels(1, ids)
    relations.set_profile_channels(2, [ids[0]])
    relations.set_profile_channels(1, [ids[1]])

    assert relations.get_selected_channel_ids(1) == [ids[1]]
    assert relations.get_selected_channel_ids(2) == [ids[0]]


def test_sync_service_requires_authorized_account_and_uses_catalog():
    db = connection()
    db.execute("INSERT INTO telegram_accounts VALUES (7, 'Cuenta', 1, 1)")
    db.commit()
    upgrade(db)
    channel_repository = TelegramChannelRepository(db)

    class Accounts:
        def get_by_id(self, account_id):
            return SimpleNamespace(id=account_id, authorized=True)

    class Manager:
        async def list_dialog_catalog(self, account_id):
            assert account_id == 7
            return dialogs()

    service = TelegramChannelSyncService(
        account_repository=Accounts(),
        channel_repository=channel_repository,
        account_manager=Manager(),
    )
    assert len(asyncio.run(service.synchronize(7))) == 4


def test_profile_routing_uses_account_and_chat_together():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    create_tables(db)
    db.executemany(
        "INSERT INTO telegram_accounts (id, name) VALUES (?, ?)",
        [(7, "Cuenta A"), (8, "Cuenta B")],
    )
    db.executemany(
        """
        INSERT INTO profiles
        (id, name, enabled, signal_source_mode)
        VALUES (?, ?, 1, 'TELEGRAM')
        """,
        [(1, "Perfil A"), (2, "Perfil B")],
    )
    db.executemany(
        """
        INSERT INTO telegram_channels
        (id, telegram_account_id, chat_id, name, enabled, available)
        VALUES (?, ?, -1001, ?, 1, 1)
        """,
        [(1, 7, "A"), (2, 8, "B")],
    )
    db.executemany(
        """
        INSERT INTO profile_telegram_channels
        (profile_id, telegram_channel_id, enabled, priority)
        VALUES (?, ?, 1, 1)
        """,
        [(1, 1), (2, 2)],
    )
    db.commit()
    repository = ProfileTelegramChannelRepository(db)

    assert [profile.id for profile in repository.get_profiles(7, -1001)] == [1]
    assert [profile.id for profile in repository.get_profiles(8, -1001)] == [2]


def test_catalog_migration_is_never_automatic():
    db = connection()
    tables_before = {
        row[0]
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }

    repository = TelegramChannelRepository(db)

    assert repository.schema_available() is False
    tables_after = {
        row[0]
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert tables_after == tables_before
    assert "telegram_channels" not in tables_after
