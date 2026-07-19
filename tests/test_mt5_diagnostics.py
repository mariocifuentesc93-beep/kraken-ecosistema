import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from database.database_manager import database_manager
from models.mt5_account import MT5Account
from repositories.mt5_diagnostics_repository import mt5_diagnostics_repository
from services.mt5_connection_diagnostics import MT5ConnectionDiagnostics


class MT5DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.original = database_manager.database
        database_manager.close()
        self.directory = Path(tempfile.mkdtemp())
        database_manager.database = self.directory / "diagnostics.db"
        database_manager.initialize()
        self.account = MT5Account(name="Bridge", login=123, password="secret", server="Bridge Markets")

    def tearDown(self):
        database_manager.close()
        database_manager.database = self.original
        shutil.rmtree(self.directory)

    @staticmethod
    def api(trading=True, symbols=True):
        api = Mock()
        api.initialize.return_value = True
        api.login.return_value = True
        api.last_error.return_value = "OK"
        api.terminal_info.return_value = SimpleNamespace(
            path="C:/MT5/terminal64.exe", connected=True, trade_allowed=trading,
            tradeapi_disabled=not trading,
        )
        api.account_info.return_value = SimpleNamespace(
            login=123, server="Bridge Markets", balance=1000.0, equity=995.0,
            currency="USD", leverage=100, trade_allowed=trading,
        )
        info = SimpleNamespace(visible=True, volume_min=0.01, volume_max=10.0,
                               volume_step=0.01, trade_tick_size=0.1, trade_tick_value=1.0,
                               trade_contract_size=100.0, trade_stops_level=5, filling_mode=1)
        api.symbol_info.return_value = info if symbols else None
        api.symbol_select.return_value = True
        api.symbol_info_tick.return_value = SimpleNamespace(bid=100.0, ask=100.1)
        return api

    def test_package_missing_and_terminal_unavailable(self):
        report = MT5ConnectionDiagnostics(package_available=False).run(self.account)
        self.assertFalse(report["success"])
        self.assertIn("paquete", report["actionable_error"])

        unavailable = MT5Account(name="Bad path", login=1, password="p", server="s", terminal_path="Z:/missing/terminal64.exe")
        report = MT5ConnectionDiagnostics(self.api(), package_available=True).run(unavailable)
        self.assertFalse(report["success"])
        self.assertIn("ejecutable", report["actionable_error"])

    def test_initialization_failure_and_invalid_credentials(self):
        api = self.api(); api.initialize.return_value = False; api.last_error.return_value = "terminal unavailable"
        self.assertIn("inicializar", MT5ConnectionDiagnostics(api, True).run(self.account)["actionable_error"])
        api = self.api(); api.login.return_value = False; api.last_error.return_value = "invalid credentials"
        self.assertIn("credenciales", MT5ConnectionDiagnostics(api, True).run(self.account)["actionable_error"])

    def test_successful_connection_persists_and_exports_reports(self):
        report = MT5ConnectionDiagnostics(self.api(), True).run(self.account)
        self.assertTrue(report["success"])
        self.assertEqual(len(report["symbols"]), 20)
        self.assertTrue(all(row["tick_available"] for row in report["symbols"]))
        self.assertIsNotNone(mt5_diagnostics_repository.latest())
        service = MT5ConnectionDiagnostics(self.api(), True)
        json_file, text_file = self.directory / "report.json", self.directory / "report.txt"
        service.export_json(report, json_file); service.export_text(report, text_file)
        self.assertTrue(json_file.exists() and text_file.exists())

    def test_trading_disabled_and_partial_symbol_availability(self):
        report = MT5ConnectionDiagnostics(self.api(trading=False), True).run(self.account)
        self.assertTrue(report["success"])
        self.assertFalse(report["trade_allowed"])
        self.assertFalse(report["algorithmic_trading_allowed"])
        self.assertIn("LIVE", report["actionable_error"])

        partial = MT5ConnectionDiagnostics(self.api(symbols=False), True).run(self.account)
        self.assertEqual(len(partial["symbols"]), 20)
        self.assertTrue(all(not row["available"] for row in partial["symbols"]))


if __name__ == "__main__":
    unittest.main()
