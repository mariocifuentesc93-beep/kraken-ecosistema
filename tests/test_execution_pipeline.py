import shutil
import tempfile
import unittest
from pathlib import Path

from database.database_manager import database_manager
from models.profile import Profile
from models.signal import Signal
from repositories.execution_timeline_repository import execution_timeline_repository
from repositories.profile_repository import profile_repository
from trading.execution_pipeline import execution_pipeline


class ExecutionPipelineTests(unittest.TestCase):
    def setUp(self):
        self.original = database_manager.database
        database_manager.close()
        self.directory = Path(tempfile.mkdtemp())
        database_manager.database = self.directory / "execution.db"
        database_manager.initialize()
        self.profile = profile_repository.create(Profile(name="Simulation", execution_mode="SIMULATION"))
        self.signal = Signal(symbol="EMASVOL10", direction="BUY", entry=100, stop_loss=90, take_profits=[110, 120, 130])

    def tearDown(self):
        database_manager.close()
        database_manager.database = self.original
        shutil.rmtree(self.directory)

    def test_all_simulation_outcomes_and_transitions(self):
        expected = {
            "pending": "QUEUED", "cancel": "CANCELLED", "expired": "EXPIRED",
            "error": "ERROR", "sl": "CLOSED", "tp1": "CLOSED",
            "tp2": "CLOSED", "tp3": "CLOSED",
        }
        for outcome, state in expected.items():
            operation = execution_pipeline.simulate(self.signal, self.profile, outcome=outcome)
            self.assertEqual(operation.status, state)

        events = execution_timeline_repository.get_all()
        states = {event["new_state"] for event in events}
        for state in ("NEW", "PARSED", "VALIDATED", "RISK_APPROVED", "QUEUED", "SIMULATED", "TP1", "TP2", "TP3", "CLOSED", "CANCELLED", "EXPIRED", "ERROR"):
            self.assertIn(state, states)
        self.assertTrue(all(event["execution_mode"] == "SIMULATION" for event in events))
        self.assertIn("simulation_success_rate", execution_timeline_repository.statistics())


if __name__ == "__main__":
    unittest.main()
