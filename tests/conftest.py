from types import SimpleNamespace
import sqlite3

import pytest

from database.signal_contract_migration import upgrade
from models.signal import Signal
from repositories.signal_repository import SignalRepository
from database.internal_telegram_publication_migration import (
    upgrade as upgrade_publication,
)
from repositories.telegram_publication_repository import (
    TelegramPublicationRepository,
)


@pytest.fixture
def unified_database(tmp_path):
    connection = sqlite3.connect(tmp_path / "signals.db")
    connection.row_factory = sqlite3.Row
    upgrade(connection)
    yield connection
    connection.close()


@pytest.fixture
def valid_signal():
    return Signal(
        source="TELEGRAM",
        telegram_account_id=7,
        chat_id=-100123,
        message_id=99,
        symbol="EmasVol20",
        direction="BUY",
        entry=73505.99,
        stop_loss=73486.47,
        take_profits=[73517.70, 73529.41, 73545.02],
        raw_message="SIGNAL - EmasVol20 buy",
    )


@pytest.fixture
def temporary_signal_repository(unified_database):
    return SignalRepository(unified_database)


@pytest.fixture
def publication_repository(tmp_path):
    connection = sqlite3.connect(tmp_path / "publications.db")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE profiles(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            operation_mode TEXT DEFAULT 'telegram'
        );
        CREATE TABLE signals(
            id INTEGER PRIMARY KEY,
            idempotency_key TEXT NOT NULL UNIQUE
        );
        CREATE TABLE telegram_accounts(
            id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 1
        );
        INSERT INTO signals(id, idempotency_key)
        VALUES (10, 'INTERNAL:LIONX100:12305');
        INSERT INTO telegram_accounts(id, enabled) VALUES (7, 1);
        """
    )
    upgrade_publication(connection)
    repository = TelegramPublicationRepository(connection)
    yield repository
    connection.close()


@pytest.fixture
def profile_factory():
    def factory(
        profile_id,
        name=None,
        enabled=True,
        signal_source_mode="TELEGRAM",
        execution_mode="SIMULATION",
        publish_internal_to_telegram=False,
        telegram_output_account_id=None,
        telegram_output_chat_id=None,
    ):
        return SimpleNamespace(
            id=profile_id,
            name=name or f"Profile {profile_id}",
            enabled=enabled,
            telegram_account_id=7,
            signal_source_mode=signal_source_mode,
            execution_mode=execution_mode,
            publish_internal_to_telegram=publish_internal_to_telegram,
            telegram_output_account_id=telegram_output_account_id,
            telegram_output_chat_id=telegram_output_chat_id,
            tp_level=1,
            execute_market=True,
        )

    return factory


@pytest.fixture
def account_factory():
    def factory(account_id, name=None, enabled=True):
        return SimpleNamespace(
            id=account_id,
            name=name or f"Account {account_id}",
            enabled=enabled,
            execution_mode="SIMULATION",
            risk_mode="PROFILE",
            risk_percent=0.0,
            risk_amount=0.0,
            fixed_lot=0.0,
            magic_number=10000 + account_id,
            comment="TEST",
            deviation=20,
        )

    return factory
