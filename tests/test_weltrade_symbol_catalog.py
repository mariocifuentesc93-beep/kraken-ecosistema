import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from config.symbols import (
    BRIDGE_CATALOG,
    WELTRADE_CATALOG,
    get_mt5_symbol,
    get_symbol_catalog,
    get_symbols,
    normalize_symbol,
)
from core.signal_parser import parse_signal
from database.weltrade_symbol_catalog_migration import downgrade, upgrade
from models.signal import Signal
from services.symbol_catalog_service import (
    AVAILABLE,
    NOT_VERIFIED,
    UNAVAILABLE,
    SymbolCatalogService,
)


EXPECTED = {
    "FXVOL20": "FX Vol 20",
    "FXVOL40": "FX Vol 40",
    "FXVOL60": "FX Vol 60",
    "FXVOL80": "FX Vol 80",
    "FXVOL99": "FX Vol 99",
    "SFXVOL20": "SFX Vol 20",
    "SFXVOL40": "SFX Vol 40",
    "SFXVOL60": "SFX Vol 60",
    "SFXVOL80": "SFX Vol 80",
    "SFXVOL99": "SFX Vol 99",
    "GAINX400": "GainX 400",
    "GAINX600": "GainX 600",
    "GAINX800": "GainX 800",
    "GAINX999": "GainX 999",
    "GAINX1200": "GainX 1200",
    "PAINX400": "PainX 400",
    "PAINX600": "PainX 600",
    "PAINX800": "PainX 800",
    "PAINX999": "PainX 999",
    "PAINX1200": "PainX 1200",
    "FLIPX1": "FlipX 1",
    "FLIPX2": "FlipX 2",
    "FLIPX3": "FlipX 3",
    "FLIPX4": "FlipX 4",
    "FLIPX5": "FlipX 5",
}


def test_fixed_catalog_has_exact_names_and_identity():
    catalog = get_symbol_catalog(WELTRADE_CATALOG)
    assert len(catalog) == 25
    assert {item["canonical_name"]: item["mt5_symbol"] for item in catalog} == EXPECTED
    assert all(item["catalog"] == WELTRADE_CATALOG for item in catalog)
    assert all(item["broker"] == "WELTRADE" for item in catalog)
    assert len(get_symbols(BRIDGE_CATALOG)) == 20


@pytest.mark.parametrize("canonical,display", EXPECTED.items())
def test_all_weltrade_names_normalize(canonical, display):
    assert normalize_symbol(display) == canonical
    assert normalize_symbol(f"  {display.lower()}  ") == canonical
    assert normalize_symbol(canonical) == canonical
    assert get_mt5_symbol(canonical) == display


@pytest.mark.parametrize(
    "text,expected",
    [
        ("SIGNAL - FX Vol 20 (BUY)", "FXVOL20"),
        ("SIGNAL - SFX Vol 99 (SELL)", "SFXVOL99"),
        ("SIGNAL - GainX 1200 (BUY)", "GAINX1200"),
        ("SIGNAL - PainX 600 (SELL)", "PAINX600"),
        ("SIGNAL - FlipX 3 (BUY)", "FLIPX3"),
        ("GAINX1200 BUY", "GAINX1200"),
        ("EMASVOL20 BUY", "EMASVOL20"),
        ("LIONX50 SELL", "LIONX50"),
    ],
)
def test_parser_resolves_weltrade_and_preserves_bridge(text, expected):
    assert parse_signal(text).symbol == expected


def _migration_connection():
    connection = sqlite3.connect(":memory:")
    connection.execute(
        "CREATE TABLE profiles(id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
    )
    connection.execute(
        """
        CREATE TABLE symbols(
            id INTEGER PRIMARY KEY,
            profile_id INTEGER NOT NULL,
            symbol TEXT NOT NULL
        )
        """
    )
    connection.executemany(
        "INSERT INTO profiles(id, name) VALUES (?, ?)",
        ((1, "Bridge 1"), (2, "Bridge 2")),
    )
    bridge = get_symbols(BRIDGE_CATALOG)
    connection.executemany(
        "INSERT INTO symbols(profile_id, symbol) VALUES (?, ?)",
        [(profile, symbol) for symbol in bridge for profile in (1, 2)],
    )
    connection.commit()
    return connection


def test_migration_is_idempotent_and_rollback_only_removes_weltrade():
    connection = _migration_connection()
    upgrade(connection)
    upgrade(connection)
    assert connection.execute("SELECT COUNT(*) FROM symbols").fetchone()[0] == 40
    assert connection.execute(
        "SELECT COUNT(*) FROM symbol_catalog WHERE catalog=?",
        (WELTRADE_CATALOG,),
    ).fetchone()[0] == 25
    logical_total = sum(
        (
            connection.execute("SELECT COUNT(*) FROM symbols").fetchone()[0],
            connection.execute("SELECT COUNT(*) FROM symbol_catalog").fetchone()[0],
        )
    )
    assert logical_total == 65
    assert connection.execute(
        "SELECT COUNT(*) FROM profile_symbol_catalog_context"
    ).fetchone()[0] == 40

    connection.execute(
        """
        INSERT INTO symbol_catalog(
            canonical_name, display_name, mt5_symbol, catalog, broker,
            category, enabled, sort_order, availability
        ) VALUES ('BRIDGE_TEST', 'Bridge Test', 'BridgeTest',
                  'BRIDGE_SYNTHETICS', 'BRIDGE MARKETS', 'TEST', 1, 1,
                  'NOT_VERIFIED')
        """
    )
    connection.commit()
    downgrade(connection)
    assert connection.execute("SELECT COUNT(*) FROM symbols").fetchone()[0] == 40
    assert connection.execute("SELECT COUNT(*) FROM symbol_catalog").fetchone()[0] == 1
    assert connection.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name='profile_symbol_catalog_context'"
    ).fetchone() is None


def test_catalog_identity_allows_same_canonical_name_in_different_catalogs():
    connection = _migration_connection()
    upgrade(connection)
    connection.execute(
        """
        INSERT INTO symbol_catalog(
            canonical_name, display_name, mt5_symbol, catalog, broker,
            category, enabled, sort_order, availability
        ) VALUES ('FXVOL20', 'Otro FX Vol 20', 'Other FX Vol 20',
                  'OTHER_SYNTHETICS', 'OTHER', 'FX_VOL', 1, 1,
                  'NOT_VERIFIED')
        """
    )
    connection.commit()
    rows = connection.execute(
        "SELECT catalog FROM symbol_catalog WHERE canonical_name='FXVOL20'"
    ).fetchall()
    assert {row[0] for row in rows} == {
        WELTRADE_CATALOG,
        "OTHER_SYNTHETICS",
    }


def test_internal_identity_uses_catalog_normalization():
    signal = Signal(
        source="INTERNAL",
        external_signal_id="77",
        symbol="  FX Vol 20 ",
        direction="BUY",
    )
    signal.validate_persistent_identity()
    assert signal.symbol == "FXVOL20"
    assert signal.idempotency_key == "INTERNAL:FXVOL20:77"


class Terminal:
    def __init__(self, available):
        self.available = available
        self.requested = []

    def symbol_info(self, symbol):
        self.requested.append(symbol)
        return object() if self.available else None


class Registry:
    def __init__(self, terminal=None):
        self.terminal = terminal
        self.requested = []

    def get(self, account_id):
        self.requested.append(account_id)
        return self.terminal


def test_resolution_is_account_scoped_and_checks_exact_mt5_name():
    service = SymbolCatalogService()
    unresolved = service.resolve_symbol(
        "FXVOL20", 7, WELTRADE_CATALOG, profile_id=3
    )
    assert unresolved.availability == NOT_VERIFIED
    assert unresolved.mt5_account_id == 7
    assert unresolved.profile_id == 3
    assert unresolved.catalog_id == WELTRADE_CATALOG
    available = Terminal(True)
    missing = Terminal(False)
    registry = Registry(available)
    resolved = service.resolve_symbol(
        "FXVOL20",
        7,
        WELTRADE_CATALOG,
        profile_id=3,
        connection_registry=registry,
    )
    assert resolved.availability == AVAILABLE
    assert registry.requested == [7]
    assert available.requested == ["FX Vol 20"]
    missing_registry = Registry(missing)
    with pytest.raises(ValueError, match="no está disponible"):
        service.require_available(
            "FXVOL20",
            7,
            WELTRADE_CATALOG,
            profile_id=3,
            connection_registry=missing_registry,
        )


def test_importing_migration_does_not_execute_it():
    connection = sqlite3.connect(":memory:")
    assert connection.execute(
        "SELECT name FROM sqlite_master WHERE name='symbol_catalog'"
    ).fetchone() is None


def test_symbol_selector_filters_without_losing_cross_catalog_selection():
    from dashboard.widgets.symbol_selector import SymbolSelector

    app = QApplication.instance() or QApplication([])
    selector = SymbolSelector()
    selector.loadCatalog(get_symbol_catalog())
    selector.setSelected(["EMASVOL20", "FXVOL20"])
    selector.catalog.setCurrentIndex(
        selector.catalog.findData(WELTRADE_CATALOG)
    )
    app.processEvents()
    assert set(selector.selectedSymbols()) == {"EMASVOL20", "FXVOL20"}
    selector.close()


def test_profile_selection_persists_bridge_and_weltrade():
    from dashboard.dialogs.profile_dialog import ProfileDialog
    from database.database_manager import database_manager
    from models.profile import Profile
    from repositories.profile_repository import profile_repository
    from repositories.symbol_repository import symbol_repository

    app = QApplication.instance() or QApplication([])
    original = database_manager.database
    directory = Path(tempfile.mkdtemp())
    database_manager.close()
    database_manager.database = directory / "profile-catalog.db"
    try:
        database_manager.initialize()
        upgrade(database_manager.connect())
        profile = profile_repository.create(Profile(name="Mixto"))
        for canonical in ("EMASVOL20", "FXVOL20"):
            definition = next(
                item
                for item in get_symbol_catalog()
                if item["canonical_name"] == canonical
            )
            symbol_repository.create(
                profile.id,
                True,
                canonical,
                definition["mt5_symbol"],
                definition["display_name"],
                "",
                1.0,
                0.01,
                100.0,
                "trade",
                definition["catalog"],
            )

        dialog = ProfileDialog(profile)
        app.processEvents()
        assert set(dialog.symbolSelector.selectedSymbols()) == {
            "EMASVOL20",
            "FXVOL20",
        }
        dialog._save_symbols(profile.id)
        enabled = {
            item.symbol
            for item in symbol_repository.get_enabled(profile.id)
        }
        assert {"EMASVOL20", "FXVOL20"} <= enabled
        assert len(enabled) == len(set(enabled))
        contexts = {
            symbol.symbol: symbol_repository.get_catalog_context(symbol.id)
            for symbol in symbol_repository.get_enabled(profile.id)
        }
        assert contexts["EMASVOL20"]["catalog_id"] == BRIDGE_CATALOG
        assert contexts["FXVOL20"]["catalog_id"] == WELTRADE_CATALOG
        dialog.close()
    finally:
        database_manager.close()
        database_manager.database = original
        shutil.rmtree(directory)
