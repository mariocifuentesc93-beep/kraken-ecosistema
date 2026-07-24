import os
from pathlib import Path
import subprocess
import sys


def test_sensitive_imports_do_not_create_or_open_sqlite(tmp_path):
    database = tmp_path / "must-not-exist.db"
    script = """
from pathlib import Path
import sys
from database.database_manager import database_manager
database_manager.database = Path(sys.argv[1])
import core.config_service
import telegram.account_manager
import core.trade_manager
assert database_manager.connection is None
assert not database_manager.database.exists()
assert 'MetaTrader5' not in sys.modules
"""
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run(
        [sys.executable, "-c", script, str(database)],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        check=True,
    )
    assert not database.exists()


def test_connect_only_opens_and_explicit_initialize_creates_schema(tmp_path):
    from database.database_manager import DatabaseManager

    database = tmp_path / "explicit.db"
    manager = DatabaseManager()
    manager.database = database
    manager.connect()
    assert manager.validate_schema({"profiles"}) == ["profiles"]
    manager.close()
    manager.initialize_new_database()
    assert manager.validate_schema({"profiles"}) == []
    manager.close()

