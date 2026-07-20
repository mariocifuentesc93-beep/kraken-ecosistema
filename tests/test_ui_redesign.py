import os
import shutil
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

from database.database_manager import database_manager
from services.trading_calendar_service import trading_calendar_service


class UiRedesignSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.original=database_manager.database; database_manager.close(); self.directory=Path(tempfile.mkdtemp()); database_manager.database=self.directory/"ui.db"; database_manager.initialize()
    def tearDown(self): database_manager.close(); database_manager.database=self.original; shutil.rmtree(self.directory)
    def test_empty_dashboard_at_1366_and_1600(self):
        from dashboard.main_window import MainWindow
        window=MainWindow()
        for width,height in ((1366,768),(1600,900)):
            window.resize(width,height); window.show(); self.app.processEvents(); self.assertFalse(window.grab().isNull()); self.assertGreaterEqual(window.menu.width(),170); self.assertEqual(window.menu.count(),18)
        self.assertIn("Perfil",window.topProfile.text()); window.close()
    def test_dashboard_demo_and_status_chips(self):
        from dashboard.main_window import MainWindow
        trading_calendar_service.load_demo(2026,7)
        window=MainWindow(); window.resize(1366,768); window.set_mt5_status(True); window.set_telegram_status(True); window.show(); self.app.processEvents()
        self.assertIn("conectado",window.topMT5.text()); self.assertGreater(window.dashboardPage.operations.rowCount(),0); self.assertFalse(window.dashboardPage.grab().isNull()); window.close()


if __name__=="__main__": unittest.main()
