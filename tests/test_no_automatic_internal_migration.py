"""Regression coverage for explicit-only global INTERNAL migrations."""

import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

from database.schema import create_tables
from database.telegram_publication_migration import upgrade


INTERNAL_ENABLED_KEY = "internal.telegram_publication.enabled"


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def existing_database(path):
    connection = sqlite3.connect(path)
    create_tables(connection)
    connection.execute(
        "DELETE FROM settings WHERE key=?",
        (INTERNAL_ENABLED_KEY,),
    )
    connection.commit()
    # Match the connection mode used by the application before taking the
    # baseline hash. Switching a DELETE-journal fixture to WAL is a physical
    # SQLite format change, not an application migration.
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    connection.close()


def test_imports_and_safe_ui_open_do_not_migrate_existing_database(tmp_path):
    database = tmp_path / "existing.db"
    existing_database(database)
    before = file_hash(database)
    script = """
import os
from pathlib import Path
import sys
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from database.database_manager import database_manager
database_manager.close()
database_manager.database = Path(sys.argv[1])
import database.schema
import models.internal_publication_config
import repositories.internal_publication_config_repository
import services.internal_publication_configuration_service
from PySide6.QtWidgets import QApplication
from dashboard.pages.internal_source_settings_page import InternalSourceSettingsPage
application = QApplication.instance() or QApplication([])
page = InternalSourceSettingsPage()
page.load()
page.close()
database_manager.close()
"""
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run(
        [sys.executable, "-c", script, str(database)],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert file_hash(database) == before
    connection = sqlite3.connect(database)
    assert connection.execute(
        "SELECT value FROM settings WHERE key=?",
        (INTERNAL_ENABLED_KEY,),
    ).fetchone() is None
    connection.close()


def test_global_configuration_is_created_only_by_explicit_upgrade(tmp_path):
    source = tmp_path / "existing.db"
    migrated = tmp_path / "migrated.db"
    existing_database(source)
    shutil.copy2(source, migrated)

    connection = sqlite3.connect(migrated)
    assert upgrade(connection) is True
    assert connection.execute(
        "SELECT value FROM settings WHERE key=?",
        (INTERNAL_ENABLED_KEY,),
    ).fetchone()[0] == "0"
    connection.close()
