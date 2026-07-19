import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from core.signal_parser import parse_signal
from core.signal_pipeline import process_signal_message
from core.signal_validator import validate_signal
from database.database_manager import database_manager
from models.profile import Profile
from repositories.signal_repository import signal_repository
from repositories.profile_repository import profile_repository


VALID = "EMASVOL10 BUY ENTRY 100 SL 90 TP1 120"


class SignalPipelineTests(unittest.TestCase):
    def setUp(self):
        self.original_database = database_manager.database
        database_manager.close()
        self.directory = Path(tempfile.mkdtemp())
        database_manager.database = self.directory / "signals.db"
        database_manager.initialize()

    def tearDown(self):
        database_manager.close()
        database_manager.database = self.original_database
        shutil.rmtree(self.directory)

    @patch("core.signal_validator.is_symbol_enabled", return_value=True)
    def test_parser_and_validator_failure_scenarios(self, _enabled):
        cases = {
            "unknown": "UNKNOWN BUY ENTRY 100 SL 90 TP1 120",
            "invalid": "hello world",
            "missing entry": "EMASVOL10 BUY SL 90 TP1 120",
            "missing sl": "EMASVOL10 BUY ENTRY 100 TP1 120",
            "missing tp": "EMASVOL10 BUY ENTRY 100 SL 90",
        }
        for label, raw in cases.items():
            valid, errors = validate_signal(parse_signal(raw))
            self.assertFalse(valid, label)
            self.assertTrue(errors, label)

    @patch("core.signal_validator.is_symbol_enabled", return_value=False)
    def test_disabled_symbol_is_rejected(self, _enabled):
        valid, errors = validate_signal(parse_signal(VALID))
        self.assertFalse(valid)
        self.assertTrue(any("deshabilitado" in item for item in errors))

    @patch("core.signal_validator.is_symbol_enabled", return_value=True)
    def test_expired_duplicate_off_and_simulation_decisions(self, _enabled):
        expired = parse_signal(VALID)
        expired.received_at = datetime.now() - timedelta(minutes=6)
        valid, errors = validate_signal(expired)
        self.assertFalse(valid)
        self.assertTrue(any("expirada" in item for item in errors))

        off = profile_repository.create(Profile(name="OFF", execution_mode="OFF"))
        rejected = process_signal_message(VALID, profile=off)
        self.assertEqual(rejected.status, "REJECTED")
        self.assertIn("OFF", rejected.rejection_reason)
        duplicate = process_signal_message(VALID, profile=off)
        self.assertIn("duplicada", duplicate.rejection_reason)

        simulation_profile = profile_repository.create(
            Profile(name="SIM", execution_mode="SIMULATION")
        )
        simulated = process_signal_message(
            "EMASVOL20 SELL ENTRY 100 SL 110 TP1 80",
            profile=simulation_profile,
        )
        self.assertEqual(simulated.status, "SIMULATED")
        self.assertEqual(simulated.execution_decision, "SIMULATED")
        self.assertEqual(simulated.metadata["trade_request"]["action"], "SIMULATED_REQUEST")

        stored = signal_repository.get_by_id(simulated.id)
        self.assertEqual(stored.raw_message, "EMASVOL20 SELL ENTRY 100 SL 110 TP1 80")
        self.assertEqual(stored.profile_id, simulation_profile.id)
