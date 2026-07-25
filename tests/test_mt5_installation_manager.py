import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from database.mt5_installation_manager_migration import downgrade, upgrade
from database.schema import create_tables
from models.mt5_terminal import MT5Terminal
from services.mt5_installation_discovery_service import (
    MT5InstallationDiscoveryService,
)
from services.mt5_terminal_launcher import MT5TerminalLauncher
from services.scanner_recovery_service import ScannerRecoveryService


def _columns(connection, table):
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def test_explicit_migration_is_idempotent_and_reversible():
    connection = sqlite3.connect(":memory:")
    create_tables(connection)
    original_accounts = _columns(connection, "mt5_accounts")
    original_profiles = _columns(connection, "profiles")

    upgrade(connection)
    upgrade(connection)
    assert connection.execute(
        "SELECT name FROM sqlite_master WHERE name='mt5_terminals'"
    ).fetchone()
    assert "mt5_terminal_id" in _columns(connection, "mt5_accounts")
    assert {"mt5_terminal_id", "catalog_id"} <= _columns(connection, "profiles")
    assert connection.execute(
        "SELECT COUNT(*) FROM settings WHERE key LIKE 'internal.scanner.%'"
    ).fetchone()[0] == 4

    downgrade(connection)
    assert _columns(connection, "mt5_accounts") == original_accounts
    assert _columns(connection, "profiles") == original_profiles
    assert connection.execute(
        "SELECT COUNT(*) FROM settings WHERE key LIKE 'internal.scanner.%'"
    ).fetchone()[0] == 0


def test_discovery_matches_origin_and_finds_inspector(tmp_path):
    install = tmp_path / "MetaTrader Scanner"
    install.mkdir()
    executable = install / "terminal64.exe"
    executable.write_bytes(b"fixture")
    data_root = tmp_path / "Terminal"
    data = data_root / "D0E820"
    indicator = data / "MQL5" / "Indicators"
    indicator.mkdir(parents=True)
    (data / "origin.txt").write_text(str(install), encoding="utf-8")
    (indicator / "KrakenBMSPInspector.mq5").write_text("fixture")
    (indicator / "KrakenBMSPInspector.ex5").write_bytes(b"fixture")

    found = MT5InstallationDiscoveryService().discover(
        [install], data_root
    )
    assert len(found) == 1
    assert found[0].data_path == str(data)
    assert found[0].origin_matches
    assert found[0].inspector_source and found[0].inspector_binary


class _ProcessBackend:
    def __init__(self, running=()):
        self.running = list(running)
        self.started = []

    def running_executables(self):
        return self.running

    def start(self, executable, arguments):
        self.started.append((executable, arguments))
        return 4321


def test_launcher_uses_portable_and_prevents_duplicate(tmp_path):
    executable = tmp_path / "terminal64.exe"
    executable.write_bytes(b"fixture")
    terminal = MT5Terminal(
        executable_path=str(executable), portable=True
    )
    backend = _ProcessBackend()
    launcher = MT5TerminalLauncher(backend)
    assert launcher.launch(terminal) == 4321
    assert backend.started[0][1] == ["/portable"]

    duplicate = MT5TerminalLauncher(_ProcessBackend([str(executable)]))
    with pytest.raises(RuntimeError, match="ya está ejecutándose"):
        duplicate.launch(terminal)


def test_scanner_recovery_only_builds_non_destructive_plan(tmp_path):
    executable = tmp_path / "install" / "terminal64.exe"
    executable.parent.mkdir()
    executable.write_bytes(b"fixture")
    original = tmp_path / "D0E"
    indicators = original / "MQL5" / "Indicators"
    indicators.mkdir(parents=True)
    (indicators / "KrakenBMSPInspector.mq5").write_text("fixture")
    (indicators / "KrakenBMSPInspector.ex5").write_bytes(b"fixture")
    current = tmp_path / "FA96"
    current.mkdir()

    plan = ScannerRecoveryService().inspect(
        executable, current, original
    )
    assert plan.strategy == "MANAGED_PORTABLE_COPY"
    assert plan.inspector_source_exists and plan.inspector_binary_exists
    assert any("distinta" in warning for warning in plan.warnings)
    assert original.exists()


def test_importing_manager_modules_does_not_touch_database(tmp_path):
    database = tmp_path / "existing.db"
    database.write_bytes(b"do-not-touch")
    before = database.read_bytes()
    __import__("services.mt5_installation_discovery_service")
    __import__("services.scanner_recovery_service")
    __import__("database.mt5_installation_manager_migration")
    assert database.read_bytes() == before
