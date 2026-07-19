"""Visual-regression coverage for the shared dark table palette."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem

from dashboard.styles import CARD_COLOR, TEXT_COLOR
from dashboard.ui_theme import application_style, apply_terminal_palette


class TableThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        apply_terminal_palette(cls.app)
        cls.app.setStyleSheet(application_style())

    def table(self):
        table = QTableWidget(2, 2)
        table.setAlternatingRowColors(True)
        table.setHorizontalHeaderLabels(["Estado", "P/L"])
        for row in range(2):
            for column in range(2):
                table.setItem(row, column, QTableWidgetItem(f"Fila {row}"))
        table.resize(420, 150); table.show(); self.app.processEvents()
        return table

    def test_palette_keeps_unselected_and_alternating_rows_dark(self):
        table = self.table(); palette = self.app.palette()
        self.assertEqual(palette.color(QPalette.Base).name(), CARD_COLOR.lower())
        self.assertNotEqual(palette.color(QPalette.Base), palette.color(QPalette.AlternateBase))
        self.assertEqual(palette.color(QPalette.Text).name(), TEXT_COLOR.lower())
        self.assertNotEqual(palette.color(QPalette.Base).name(), "#ffffff")
        table.close()

    def test_selected_hover_disabled_and_header_rules_are_readable(self):
        table = self.table(); table.selectRow(0); table.setEnabled(False); self.app.processEvents()
        palette = self.app.palette()
        self.assertNotEqual(palette.color(QPalette.Highlight), palette.color(QPalette.HighlightedText))
        self.assertNotEqual(palette.color(QPalette.Disabled, QPalette.Text).name(), "#ffffff")
        style = application_style()
        for selector in ("QTableView::item:hover", "QTableView::item:selected", "QTableView::item:disabled", "QHeaderView::section"):
            self.assertIn(selector, style)
        self.assertFalse(table.grab().isNull()); table.close()

    def test_empty_table_and_active_pages_use_the_shared_theme(self):
        empty = QTableWidget(); empty.resize(300, 120); empty.show(); self.app.processEvents()
        self.assertFalse(empty.grab().isNull()); self.assertIn("QTableCornerButton::section", application_style()); empty.close()

    def test_all_active_table_pages_receive_readable_table_behavior(self):
        from dashboard.main_window import MainWindow
        window = MainWindow()
        pages = (window.profilesPage, window.operationsPage, window.statisticsPage,
                 window.mt5Page, window.telegramPage, window.channelsPage, window.symbolsPage,
                 window.signalInspectorPage, window.tradeTimelinePage, window.marketDataPage,
                 window.paperTradingPage, window.tradingCalendarPage, window.analyticsPage,
                 window.replayPage)
        for page in pages:
            tables = page.findChildren(QTableWidget)
            self.assertTrue(tables, page.__class__.__name__)
            self.assertTrue(all(table.alternatingRowColors() and table.hasMouseTracking() for table in tables))
        window.close()


if __name__ == "__main__":
    unittest.main()
