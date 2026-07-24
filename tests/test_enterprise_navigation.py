import os
import shutil
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from dashboard.navigation import FULL_TEXT_ROLE
from database.database_manager import database_manager


class EnterpriseNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.settings = QSettings("KrakenBot", "EnterpriseUI")
        self.settings.remove("navigation")
        self.settings.setValue("sidebar/collapsed", False)
        self.settings.sync()
        self.original_database = database_manager.database
        database_manager.close()
        self.directory = Path(tempfile.mkdtemp())
        database_manager.database = self.directory / "navigation.db"
        database_manager.initialize()

    def tearDown(self):
        cleanup = QSettings("KrakenBot", "EnterpriseUI")
        cleanup.remove("navigation")
        cleanup.setValue("sidebar/collapsed", False)
        cleanup.sync()
        database_manager.close()
        database_manager.database = self.original_database
        shutil.rmtree(self.directory)

    def create_window(self):
        from dashboard.main_window import MainWindow

        window = MainWindow()
        window.show()
        self.app.processEvents()
        return window

    def test_categories_icons_and_animated_states(self):
        window = self.create_window()
        self.assertEqual(
            list(window.navigation_groups),
            ["OPERATION", "TRADING", "MARKET", "ANALYSIS", "CONFIGURATION"],
        )
        for header, children in window.navigation_groups.values():
            self.assertGreaterEqual(header.sizeHint().height(), 38)
            for item in children:
                self.assertFalse(item.icon().isNull())
        self.assertEqual(window.menu._hover_animation.duration(), 140)
        self.assertEqual(window.menu._selection_animation.duration(), 180)
        window.close()

    def test_groups_and_sidebar_state_are_persistent(self):
        window = self.create_window()
        header, children = window.navigation_groups["OPERATION"]
        window.toggle_navigation_group(header)
        self.assertTrue(all(item.isHidden() for item in children))
        persisted = QSettings("KrakenBot", "EnterpriseUI")
        self.assertTrue(persisted.value("navigation/groups/OPERATION", False, type=bool))

        window.set_sidebar_collapsed(True)
        self.assertEqual(window.sidebar.width(), 64)
        self.assertTrue(header.isHidden())
        self.assertTrue(all(item.text() == "" for item in window.page_items.values()))
        self.assertTrue(persisted.value("sidebar/collapsed", False, type=bool))
        window.close()

        restored = self.create_window()
        self.assertEqual(restored.sidebar.width(), 64)
        self.assertTrue(all(item.isHidden() for item in restored.navigation_groups["OPERATION"][1]))
        restored.set_sidebar_collapsed(False)
        self.assertEqual(restored.sidebar.width(), 210)
        self.assertEqual(restored.page_items["Dashboard"].text(), "Dashboard")
        restored.close()

    def test_page_fade_restore_and_keyboard_navigation(self):
        window = self.create_window()
        analytics = window.page_items["Analíticas"]
        window.menu.setCurrentItem(analytics)
        self.app.processEvents()
        self.assertEqual(window.stack.currentIndex(), 15)
        self.assertEqual(window.page_transition.duration(), 175)
        persisted = QSettings("KrakenBot", "EnterpriseUI")
        self.assertEqual(persisted.value("navigation/last_page", "", type=str), "Analíticas")
        window.close()

        restored = self.create_window()
        self.assertEqual(restored.stack.currentIndex(), 15)
        self.assertEqual(restored.menu.currentItem().data(FULL_TEXT_ROLE), "Analíticas")

        restored.menu.setFocus()
        QTest.keyClick(restored.menu, Qt.Key_Home)
        self.assertEqual(restored.menu.currentItem().data(FULL_TEXT_ROLE), "Dashboard")
        QTest.keyClick(restored.menu, Qt.Key_Down)
        self.assertEqual(restored.menu.currentItem().data(FULL_TEXT_ROLE), "Operaciones")

        header = restored.navigation_groups["TRADING"][0]
        restored.menu.setCurrentItem(header)
        QTest.keyClick(restored.menu, Qt.Key_Return)
        self.assertTrue(all(item.isHidden() for item in restored.navigation_groups["TRADING"][1]))
        restored.close()


if __name__ == "__main__":
    unittest.main()
