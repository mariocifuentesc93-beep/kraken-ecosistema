import os
import shutil
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from dashboard.pages.dashboard_page import KpiCard, KpiGlyph
from database.database_manager import database_manager


class DashboardPolishTests(unittest.TestCase):
    RESOLUTIONS = ((1366, 768), (1600, 900), (1920, 1080), (2560, 1440), (3840, 2160))

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.original = database_manager.database
        database_manager.close()
        self.directory = Path(tempfile.mkdtemp())
        database_manager.database = self.directory / "dashboard-polish.db"
        database_manager.initialize()

    def tearDown(self):
        database_manager.close()
        database_manager.database = self.original
        shutil.rmtree(self.directory)

    def test_dashboard_geometry_matches_enterprise_standard(self):
        from dashboard.main_window import MainWindow

        window = MainWindow()
        window.show()
        page = window.dashboardPage
        cards = list(page.kpis.values())
        self.assertEqual(len(cards), 12)
        self.assertTrue(all(isinstance(card, KpiCard) for card in cards))
        self.assertEqual(len(page.findChildren(KpiGlyph)), 12)

        for width, height in self.RESOLUTIONS:
            window.resize(width, height)
            self.app.processEvents()
            self.assertEqual(window.size().width(), width)
            self.assertEqual(window.size().height(), height)
            self.assertEqual({card.height() for card in cards}, {KpiCard.HEIGHT})
            self.assertLessEqual(max(card.width() for card in cards) - min(card.width() for card in cards), 1)
            for index, card in enumerate(cards):
                row, column, row_span, column_span = page.cards.getItemPosition(index)
                self.assertEqual((row, column, row_span, column_span), (index // 4, index % 4, 1, 1))
            self.assertEqual({glyph.size().width() for glyph in page.findChildren(KpiGlyph)}, {KpiCard.ICON_SIZE})
            self.assertEqual(page.side_column.width(), 350)
            self.assertGreaterEqual(page.side_column.x(), page.curve.geometry().right())
            self.assertGreater(page.quick_actions.y(), page.connectivity.geometry().bottom())
            self.assertEqual(page.operations_panel.height(), page.signals_panel.height())
            self.assertEqual(page.operations_panel.y(), page.signals_panel.y())

        window.close()

    def test_recent_tables_are_compact_and_identical(self):
        from dashboard.main_window import MainWindow

        window = MainWindow()
        for table in (window.dashboardPage.operations, window.dashboardPage.signals):
            self.assertEqual(table.verticalHeader().defaultSectionSize(), 22)
            self.assertEqual(table.verticalHeader().minimumSectionSize(), 22)
            self.assertEqual(table.horizontalHeader().height(), 22)
            self.assertIn("font-size:9px", table.styleSheet())
        window.close()


if __name__ == "__main__":
    unittest.main()
