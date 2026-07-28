import os
import sqlite3
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from dashboard.pages.internal_source_settings_page import (
    InternalSourceSettingsPage,
)
from dashboard.pages.mt5_terminals_page import MT5TerminalsPage
from database.mt5_installation_manager_migration import (
    upgrade as installation_upgrade,
)
from database.mt5_terminal_capabilities_migration import downgrade, upgrade
from database.schema import create_tables
from internal.csv_watcher import InternalCsvWatcher
from internal.source import InternalSignalSource, default_internal_directory
from models.internal_publication_config import InternalPublicationConfig
from models.mt5_terminal import MT5Terminal
from services.mt5_terminal_diagnostic_service import (
    MT5TerminalDiagnosticService,
)
from services.runtime_coordinator import resolve_internal_directory


def columns(connection):
    return {
        row[1]
        for row in connection.execute("PRAGMA table_info(mt5_terminals)")
    }


def migrated_connection():
    connection = sqlite3.connect(":memory:")
    create_tables(connection)
    installation_upgrade(connection)
    connection.execute(
        """
        INSERT INTO mt5_terminals(
            id, name, broker, executable_path, data_path, role, active
        ) VALUES
            (1, 'Principal', 'BRIDGE MARKETS', 'C:/principal/terminal64.exe',
             'D0E', 'TRADING', 1),
            (6, 'Scanner antiguo', 'UNKNOWN', 'C:/scaner/terminal64.exe',
             'FA96', 'SCANNER', 0)
        """
    )
    connection.commit()
    return connection


def test_migration_maps_legacy_roles_and_is_idempotent():
    connection = migrated_connection()
    upgrade(connection)
    upgrade(connection)

    principal = connection.execute(
        "SELECT can_trade, can_scan FROM mt5_terminals WHERE id=1"
    ).fetchone()
    scanner = connection.execute(
        "SELECT can_trade, can_scan FROM mt5_terminals WHERE id=6"
    ).fetchone()
    assert principal == (1, 0)
    assert scanner == (0, 1)
    assert {
        "process_status",
        "trading_connection_status",
        "scanner_status",
        "account_match_status",
    } <= columns(connection)


def test_terminal_can_trade_and_scan_with_one_executable_identity():
    connection = migrated_connection()
    upgrade(connection)
    connection.execute(
        "UPDATE mt5_terminals SET can_trade=1, can_scan=1 WHERE id=1"
    )
    connection.commit()
    assert connection.execute(
        "SELECT can_trade, can_scan FROM mt5_terminals WHERE id=1"
    ).fetchone() == (1, 1)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            """
            INSERT INTO mt5_terminals(
                name, executable_path, role, can_trade, can_scan
            ) VALUES('Duplicada', 'C:/principal/terminal64.exe',
                     'SCANNER', 0, 1)
            """
        )


def test_migration_preserves_trading_associations():
    connection = migrated_connection()
    connection.execute(
        "UPDATE mt5_accounts SET mt5_terminal_id=1 WHERE id=1"
    )
    connection.execute(
        "UPDATE profiles SET mt5_terminal_id=1 WHERE id=1"
    )
    connection.commit()
    before = (
        connection.execute(
            "SELECT mt5_terminal_id FROM mt5_accounts WHERE id=1"
        ).fetchone(),
        connection.execute(
            "SELECT mt5_terminal_id FROM profiles WHERE id=1"
        ).fetchone(),
    )
    upgrade(connection)
    after = (
        connection.execute(
            "SELECT mt5_terminal_id FROM mt5_accounts WHERE id=1"
        ).fetchone(),
        connection.execute(
            "SELECT mt5_terminal_id FROM profiles WHERE id=1"
        ).fetchone(),
    )
    assert after == before


def test_rollback_removes_only_capability_structures():
    connection = migrated_connection()
    original = columns(connection)
    upgrade(connection)
    downgrade(connection)
    assert columns(connection) == original
    assert connection.execute(
        "SELECT COUNT(*) FROM mt5_terminals"
    ).fetchone()[0] == 2


def test_importing_migration_has_no_automatic_side_effect(tmp_path):
    database = tmp_path / "unchanged.db"
    database.write_bytes(b"unchanged")
    before = database.read_bytes()
    __import__("database.mt5_terminal_capabilities_migration")
    assert database.read_bytes() == before


def test_model_preserves_legacy_role_compatibility():
    trading = MT5Terminal(role="TRADING")
    scanner = MT5Terminal(role="SCANNER")
    hybrid = MT5Terminal(role="TRADING", can_trade=True, can_scan=True)
    assert trading.can_trade and not trading.can_scan
    assert scanner.can_scan and not scanner.can_trade
    assert hybrid.capabilities_label == "TRADING + SCANNER"


def test_common_files_and_official_csv_pattern(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    expected = (
        tmp_path / "MetaQuotes" / "Terminal" / "Common" / "Files"
    )
    assert default_internal_directory() == expected
    source = InternalSignalSource(directory=expected)
    watcher = InternalCsvWatcher(expected)
    assert source.pattern == "Kraken_BMSP_*.csv"
    assert watcher.pattern == "Kraken_BMSP_*.csv"


def test_account_mismatch_does_not_block_scanner():
    diagnostic = MT5TerminalDiagnosticService.evaluate(
        process_running=True,
        inspector_active=True,
        expected_login=243274,
        detected_login=7911007,
        detected_server="BridgeMarkets-MT5",
    )
    assert diagnostic.account_match_status == "MISMATCH"
    assert diagnostic.trading_connection_status == "NOT_VALIDATED"
    assert diagnostic.scanner_usable


class MemoryConfig:
    def __init__(self):
        self.config = InternalPublicationConfig()

    def get(self):
        return self.config

    def save(self, config):
        self.config = config
        return config


class MemorySettings:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get(self, key, default=None):
        return self.values.get(key, default)

    def get_bool(self, key, default=False):
        return str(self.get(key, int(default))).lower() in {"1", "true"}

    def get_int(self, key, default=0):
        try:
            return int(self.get(key, default))
        except (TypeError, ValueError):
            return default

    def set(self, key, value):
        self.values[key] = str(value)


class EmptyAccounts:
    def reload(self):
        return True

    def get_accounts(self):
        return []

    def get_account(self, _account_id):
        return None

    def connection_state(self, _account_id=None):
        return "DISCONNECTED"


class TerminalRepository:
    def __init__(self, terminals):
        self.terminals = list(terminals)

    def get_scanner_capable(self):
        return [item for item in self.terminals if item.can_scan]

    def get_by_id(self, terminal_id):
        return next(
            (item for item in self.terminals if item.id == terminal_id),
            None,
        )

    def get_all(self):
        return list(self.terminals)

    def _available(self):
        return True


class TerminalAccounts:
    def get_all(self):
        return [
            SimpleNamespace(
                login=243274,
                server="BridgeMarkets-MT5",
                mt5_terminal_id=1,
            )
        ]


def test_scanner_selector_accepts_hybrid_and_shows_mismatch(tmp_path):
    app = QApplication.instance() or QApplication([])
    csv = tmp_path / "Kraken_BMSP_EmasVol10.csv"
    csv.write_text("fixture", encoding="utf-8")
    terminal = MT5Terminal(
        id=1,
        name="Principal",
        role="TRADING",
        can_trade=True,
        can_scan=True,
        process_status="RUNNING",
        scanner_status="ACTIVE",
        account_match_status="MISMATCH",
    )
    settings = MemorySettings(
        {
            "internal.scanner.enabled": "1",
            "internal.scanner.mt5_terminal_id": "1",
            "internal.scanner.output_directory": str(tmp_path),
            "internal.scanner.auto_start_terminal": "0",
        }
    )
    page = InternalSourceSettingsPage(
        config_repository=MemoryConfig(),
        account_manager=EmptyAccounts(),
        destinations_provider=lambda _account_id: [],
        test_sender=lambda *_args: None,
        scanner_settings_repository=settings,
        terminal_repository=TerminalRepository([terminal]),
    )
    app.processEvents()
    assert page.scanner_terminal_combo.currentData() == 1
    assert "TRADING + SCANNER" in page.scanner_terminal_combo.currentText()
    assert page.scanner_process_status.text() == "RUNNING"
    assert page.scanner_inspector_status.text() == "ACTIVE"
    assert "ACCOUNT_MISMATCH" in page.scanner_account_status.text()
    assert page.scanner_last_file.text() == str(csv)


def test_scanner_selector_excludes_trade_only_terminal():
    app = QApplication.instance() or QApplication([])
    repository = TerminalRepository(
        [MT5Terminal(id=1, name="Trading", role="TRADING")]
    )
    page = InternalSourceSettingsPage(
        config_repository=MemoryConfig(),
        account_manager=EmptyAccounts(),
        destinations_provider=lambda _account_id: [],
        test_sender=lambda *_args: None,
        scanner_settings_repository=MemorySettings(),
        terminal_repository=repository,
    )
    app.processEvents()
    assert page.scanner_terminal_combo.count() == 1


def test_scanner_settings_are_global_and_profile_independent(tmp_path):
    app = QApplication.instance() or QApplication([])
    terminal = MT5Terminal(
        id=1,
        name="Hybrid",
        can_trade=True,
        can_scan=True,
    )
    settings = MemorySettings()
    page = InternalSourceSettingsPage(
        config_repository=MemoryConfig(),
        account_manager=EmptyAccounts(),
        destinations_provider=lambda _account_id: [],
        test_sender=lambda *_args: None,
        scanner_settings_repository=settings,
        terminal_repository=TerminalRepository([terminal]),
    )
    page.scanner_terminal_combo.setCurrentIndex(
        page.scanner_terminal_combo.findData(1)
    )
    page.scanner_enabled_checkbox.setChecked(True)
    page.scanner_output_path.setText(str(tmp_path))
    page._save_scanner_settings()
    assert settings.values == {
        "internal.scanner.enabled": "1",
        "internal.scanner.mt5_terminal_id": "1",
        "internal.scanner.output_directory": str(tmp_path),
        "internal.scanner.auto_start_terminal": "0",
    }


def test_runtime_resolves_scanner_common_files_without_profiles(tmp_path):
    common_files = tmp_path / "MetaQuotes" / "Terminal" / "Common" / "Files"
    settings = MemorySettings(
        {
            "internal.scanner.enabled": "1",
            "internal.scanner.output_directory": str(common_files),
        }
    )
    assert resolve_internal_directory(settings, tmp_path / "fallback") == (
        common_files
    )


def test_terminal_table_keeps_ids_with_rows_when_sorting_is_enabled():
    app = QApplication.instance() or QApplication([])
    repository = TerminalRepository(
        [
            MT5Terminal(id=6, name="Scanner", role="SCANNER"),
            MT5Terminal(
                id=1,
                name="Principal",
                role="TRADING",
                can_trade=True,
                can_scan=True,
            ),
        ]
    )
    page = MT5TerminalsPage(
        repository=repository,
        account_repository=TerminalAccounts(),
    )
    page.table.setSortingEnabled(True)
    page.refresh()
    app.processEvents()
    rows = {
        page.table.item(row, 0).text(): page.table.item(row, 1).text()
        for row in range(page.table.rowCount())
    }
    assert rows == {"1": "Principal", "6": "Scanner"}
