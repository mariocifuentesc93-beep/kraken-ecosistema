import os
import shutil
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication, QPushButton

from dashboard.icons import ICON_SIZE, colored_icon, semantic_icon
from database.database_manager import database_manager


class EnterpriseIconSystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.original_database = database_manager.database
        database_manager.close()
        self.directory = Path(tempfile.mkdtemp())
        database_manager.database = self.directory / "icons.db"
        database_manager.initialize()

    def tearDown(self):
        database_manager.close()
        database_manager.database = self.original_database
        shutil.rmtree(self.directory)

    def test_lucide_is_the_only_interface_icon_source(self):
        self.assertFalse(colored_icon("settings").isNull())
        self.assertFalse(semantic_icon("Guardar").isNull())
        source_root = Path(__file__).resolve().parents[1] / "dashboard"
        forbidden = "✅❌⚠ℹ🔔🔍➕✏🗑▶■⟳⚙📊📈📉💾📁📋🔄"
        for source in source_root.rglob("*.py"):
            if not source.is_file():
                continue
            content = source.read_text(encoding="utf-8")
            self.assertFalse(any(symbol in content for symbol in forbidden), source)

    def test_shell_cards_buttons_toolbar_sidebar_and_chips_share_contract(self):
        from dashboard.main_window import MainWindow

        window = MainWindow()
        window.show()
        self.app.processEvents()
        self.assertEqual(window.toolbar.iconSize(), QSize(ICON_SIZE, ICON_SIZE))
        self.assertEqual(window.menu.iconSize(), QSize(ICON_SIZE, ICON_SIZE))
        self.assertEqual(len(window.status_icon_chips), 6)
        for chip in window.status_icon_chips:
            self.assertTrue(chip.property("enterpriseIconChip"))
        from dashboard.pages.dashboard_page import KpiGlyph
        for glyph in window.dashboardPage.findChildren(KpiGlyph):
            self.assertFalse(glyph.svg_icon.isNull())
        for button in window.findChildren(QPushButton):
            if not semantic_icon(button.text()).isNull() and button.property("calendarState") is None:
                self.assertFalse(button.icon().isNull(), button.text())
                self.assertEqual(button.iconSize(), QSize(ICON_SIZE, ICON_SIZE))
        window.close()

    def test_dialog_buttons_are_normalized_when_shown(self):
        from dashboard.dialogs.settings_dialog import SettingsDialog
        from dashboard.icons import install_icon_system

        install_icon_system(self.app)
        dialog = SettingsDialog()
        dialog.show()
        self.app.processEvents()
        for button in (dialog.btnSave, dialog.btnCancel):
            self.assertFalse(button.icon().isNull())
            self.assertEqual(button.iconSize(), QSize(ICON_SIZE, ICON_SIZE))
        dialog.close()


if __name__ == "__main__":
    unittest.main()
