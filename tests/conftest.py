from types import SimpleNamespace
import sqlite3
import shutil

import sys

import pytest

from database.signal_contract_migration import upgrade
from models.signal import Signal
from repositories.signal_repository import SignalRepository


@pytest.fixture(scope="session", autouse=True)
def isolate_test_session_from_production_database(tmp_path_factory):
    """Redirect every non-injected repository to a disposable DB copy."""
    from database.database_manager import database_manager

    production_database = database_manager.database
    isolated_directory = tmp_path_factory.mktemp("kraken-session-db")
    isolated_database = isolated_directory / "kraken-test.db"
    database_manager.close()
    if production_database.is_file():
        shutil.copy2(production_database, isolated_database)
    else:
        connection = sqlite3.connect(isolated_database)
        try:
            from database.schema import create_tables

            create_tables(connection)
        finally:
            connection.close()
    database_manager.database = isolated_database
    try:
        yield isolated_database
    finally:
        database_manager.close()
        database_manager.database = production_database


@pytest.fixture(autouse=True)
def isolate_phase_tests_from_prior_mt5_imports(request):
    """Keep no-MT5 contract checks independent of collection order.

    The professional visual suite also contains explicit MT5 integration
    tests, which import the adapter during collection. The signal-flow tests
    below validate a separate injected path and must observe a clean module
    registry to prove that path does not import MT5 itself.
    """

    isolated_files = {
        "test_internal_execution_guard.py",
        "test_telegram_ingestion_flow.py",
        "test_telegram_signal_flow.py",
    }
    if request.path.name not in isolated_files:
        yield
        return

    isolated_modules = ["MetaTrader5"]
    if request.path.name == "test_telegram_signal_flow.py":
        isolated_modules.append("database.database_manager")
    previous = {
        name: sys.modules.pop(name, None)
        for name in isolated_modules
    }
    try:
        yield
    finally:
        for name, module in previous.items():
            if module is not None:
                sys.modules[name] = module
from database.telegram_publication_migration import (
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
    ):
        return SimpleNamespace(
            id=profile_id,
            name=name or f"Profile {profile_id}",
            enabled=enabled,
            telegram_account_id=7,
            signal_source_mode=signal_source_mode,
            execution_mode=execution_mode,
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
