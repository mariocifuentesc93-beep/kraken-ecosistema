import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from database.database_manager import database_manager
from models.mt5_account import MT5Account
from models.profile import Profile
from models.telegram_account import TelegramAccount
from repositories.mt5_account_repository import mt5_account_repository
from repositories.mt5_diagnostics_repository import mt5_diagnostics_repository
from repositories.profile_repository import profile_repository
from repositories.profile_telegram_repository import profile_telegram_channel_repository
from repositories.telegram_account_repository import telegram_account_repository
from repositories.telegram_diagnostics_repository import telegram_diagnostics_repository
from services.live_readiness_certification import live_readiness_certification


class LiveReadinessTests(unittest.TestCase):
    def setUp(self):
        self.original = database_manager.database; database_manager.close()
        self.directory = Path(tempfile.mkdtemp()); database_manager.database = self.directory / "ready.db"; database_manager.initialize()

    def tearDown(self):
        database_manager.close(); database_manager.database = self.original; shutil.rmtree(self.directory)

    def ready_environment(self):
        mt5 = mt5_account_repository.create(MT5Account(name="MT5", login=1, password="p", server="s"))
        telegram = telegram_account_repository.create(TelegramAccount(name="TG", phone="+10000000000", api_id=1, api_hash="h", session_name="ready", connected=True, authorized=True))
        profile = profile_repository.create(Profile(name="Ready", default_mt5_account=mt5.id, telegram_account_id=telegram.id,
            execution_mode="SIMULATION", risk_percent=1, max_daily_loss=100, max_open_trades=2, max_lot=1))
        profile_telegram_channel_repository.create_channel(1, "Ready channel", profile.id, telegram.id)
        symbols = [{"tick_available": True} for _ in range(20)]
        mt5_diagnostics_repository.save_diagnostic({"account_id": mt5.id, "success": True, "trade_allowed": True,
            "algorithmic_trading_allowed": True, "symbols": symbols, "connected_timestamp": "2026-01-01T00:00:00+00:00"})
        telegram_diagnostics_repository.save_diagnostic({"account_id": telegram.id, "status": "AUTHORIZED", "success": True,
            "authorized": True, "connected": True, "channels": [{"accessible": True, "enabled": True}], "connected_timestamp": "2026-01-01T00:00:00+00:00"})
        backup_dir = self.directory / "backups"; backup_dir.mkdir(); (backup_dir / "ready.db").write_text("backup")
        return profile

    @staticmethod
    def quote(fresh=True):
        return {"source": "MT5", "fresh": fresh, "stale_reason": "Tick MT5 vencido." if not fresh else ""}

    def test_fully_ready_environment_and_exports(self):
        self.ready_environment()
        with patch("services.live_readiness_certification.mt5_connector.is_connected", return_value=True), \
             patch("services.live_readiness_certification.market_data_service.quote", return_value=self.quote()):
            report = live_readiness_certification.evaluate()
        self.assertEqual(report["score"], 100); self.assertTrue(report["available"])
        live_readiness_certification.export(report, self.directory / "ready.json", "json")
        live_readiness_certification.export(report, self.directory / "ready.html", "html")
        live_readiness_certification.export(report, self.directory / "ready.txt", "txt")
        self.assertTrue((self.directory / "ready.html").exists())
        self.assertIn("BLOCKED", report["live_execution"])

    def test_missing_mt5_missing_telegram_and_missing_profile(self):
        report = live_readiness_certification.evaluate()
        self.assertFalse(report["available"])
        self.assertTrue(report["blocking_report"])
        profile = profile_repository.create(Profile(name="No MT5", risk_percent=1, max_daily_loss=1, max_open_trades=1))
        self.assertFalse(live_readiness_certification.evaluate()["available"])
        profile.telegram_account_id = None; profile_repository.update(profile)
        self.assertFalse(live_readiness_certification.evaluate()["available"])

    def test_invalid_risk_and_stale_market_data(self):
        profile = self.ready_environment(); profile.risk_percent = 0; profile_repository.update(profile)
        with patch("services.live_readiness_certification.mt5_connector.is_connected", return_value=True), \
             patch("services.live_readiness_certification.market_data_service.quote", return_value=self.quote()):
            self.assertFalse(live_readiness_certification.evaluate()["available"])
        profile.risk_percent = 1; profile_repository.update(profile)
        with patch("services.live_readiness_certification.mt5_connector.is_connected", return_value=True), \
             patch("services.live_readiness_certification.market_data_service.quote", return_value=self.quote(False)):
            report = live_readiness_certification.evaluate()
        self.assertIn("Tick MT5 vencido.", report["blocking_report"])

    def test_database_failure(self):
        with patch.object(database_manager, "execute", side_effect=RuntimeError("SQLite unavailable")):
            report = live_readiness_certification.evaluate()
        self.assertTrue(any(item["name"] == "SQLite healthy" and item["status"] == "FAIL" for item in report["items"]))


if __name__ == "__main__":
    unittest.main()
