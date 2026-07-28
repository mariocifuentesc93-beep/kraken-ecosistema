from pathlib import Path

from database.database_manager import database_manager


def test_pytest_session_never_targets_production_database():
    production = (
        Path(__file__).resolve().parents[1] / "database" / "kraken.db"
    ).resolve()
    assert database_manager.database.resolve() != production
    assert database_manager.database.name == "kraken-test.db"
