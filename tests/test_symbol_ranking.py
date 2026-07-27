import shutil
import tempfile
from datetime import date
from pathlib import Path

from database.database_manager import database_manager
from models.operation import Operation
from models.profile import Profile
from models.signal import Signal
from repositories.operation_milestone_repository import (
    operation_milestone_repository,
)
from repositories.operation_repository import operation_repository
from repositories.profile_repository import profile_repository
from services.symbol_ranking_service import symbol_ranking_service


def test_symbol_ranking_uses_persistent_tp_milestones():
    original = database_manager.database
    database_manager.close()
    directory = Path(tempfile.mkdtemp())
    database_manager.database = directory / "ranking.db"
    database_manager.initialize()
    try:
        profile = profile_repository.create(Profile(
            name="Demo", execution_mode="DEMO",
            signal_source_mode="INTERNAL",
        ))
        signal = Signal(
            source="INTERNAL",
            external_signal_id="ranking-1",
            symbol="LIONX40",
            direction="SELL",
            entry=140.0,
            stop_loss=150.0,
            take_profits=[130.0, 120.0, 110.0],
        )
        operation = operation_repository.create(Operation(
            signal=signal,
            profile=profile,
            ticket=123,
            status="CLOSED",
            profit=25.0,
            opened_at="2026-07-01 10:00:00",
            closed_at="2026-07-01 11:00:00",
        ))
        operation_milestone_repository.save_levels(operation, "DEMO")
        operation_milestone_repository.record(operation, "TP1", 130, "DEMO")
        operation_milestone_repository.record(operation, "TP2", 120, "DEMO")
        assert not operation_milestone_repository.record(
            operation, "TP2", 120, "DEMO"
        )

        rows = symbol_ranking_service.ranking({
            "start": date(2026, 7, 1),
            "end": date(2026, 7, 31),
            "mode": "DEMO",
            "source": "INTERNAL",
        })

        assert len(rows) == 1
        assert rows[0]["symbol"] == "LIONX40"
        assert rows[0]["tp1"] == 1
        assert rows[0]["tp2"] == 1
        assert rows[0]["tp3"] == 0
        assert rows[0]["sl"] == 0
        assert rows[0]["tp1_rate"] == 100
        assert rows[0]["rank"] == 1
    finally:
        database_manager.close()
        database_manager.database = original
        shutil.rmtree(directory)
