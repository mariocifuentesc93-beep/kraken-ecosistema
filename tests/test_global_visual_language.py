import os
import shutil
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QComboBox, QFrame, QLabel, QLineEdit, QPushButton, QTableView

from dashboard.ui_theme import application_style
from database.database_manager import database_manager


class GlobalVisualLanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.original = database_manager.database
        database_manager.close()
        self.directory = Path(tempfile.mkdtemp())
        database_manager.database = self.directory / "visual-language.db"
        database_manager.initialize()

    def tearDown(self):
        database_manager.close()
        database_manager.database = self.original
        shutil.rmtree(self.directory)

    def test_pages_do_not_define_local_styles(self):
        root = Path(__file__).resolve().parents[1] / "dashboard"
        sources = [*(root / "pages").glob("*.py"), root / "widgets" / "enterprise.py"]
        for source in sources:
            self.assertNotIn("setStyleSheet", source.read_text(encoding="utf-8"), source.name)

    def test_every_page_uses_the_central_component_states(self):
        from dashboard.main_window import MainWindow

        window = MainWindow()
        pages = [window.stack.widget(index) for index in range(window.stack.count())]
        for index, page in enumerate(pages):
            if index == 0:
                self.assertTrue(any(label.property("role") == "pageTitle" for label in page.findChildren(QLabel)))
            else:
                self.assertEqual(len(page.findChildren(QFrame, "EnterprisePageHeader")), 1)
            for control_type in (QPushButton, QComboBox, QLineEdit, QTableView):
                for control in page.findChildren(control_type):
                    self.assertEqual(control.styleSheet(), "", f"local style on {page.__class__.__name__}")
        window.close()

    def test_theme_defines_hover_selected_disabled_and_semantic_components(self):
        theme = application_style()
        for token in (
            'QLabel[role="pageTitle"]',
            'QLabel[role="subtitle"]',
            'QLabel[role="information"]',
            'QFrame[role="card"]',
            'QWidget[role="toolbar"]',
            'QLineEdit[role="search"]',
            "QPushButton:hover",
            "QPushButton:checked",
            "QPushButton:disabled",
            "QTableWidget::item:selected",
            "QComboBox:disabled",
        ):
            self.assertIn(token, theme)


if __name__ == "__main__":
    unittest.main()
