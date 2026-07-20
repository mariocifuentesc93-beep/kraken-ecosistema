import os
import shutil
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QGridLayout, QHBoxLayout, QVBoxLayout

from dashboard.layout_manager import enterprise_layout
from database.database_manager import database_manager


class EnterpriseLayoutTests(unittest.TestCase):
    RESOLUTIONS = ((1366, 768), (1600, 900), (1920, 1080), (2560, 1440), (3840, 2160))

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.original = database_manager.database
        database_manager.close()
        self.directory = Path(tempfile.mkdtemp())
        database_manager.database = self.directory / "layout.db"
        database_manager.initialize()

    def tearDown(self):
        database_manager.close()
        database_manager.database = self.original
        shutil.rmtree(self.directory)

    def test_shell_and_every_page_follow_global_layout_contract(self):
        from dashboard.main_window import MainWindow

        window = MainWindow()
        window.show()
        pages = [window.stack.widget(index) for index in range(window.stack.count())]
        self.assertEqual(len(pages), 18)
        for page in pages:
            self.assertTrue(page.property("enterpriseLayoutManaged"), page.__class__.__name__)
            self.assertIsInstance(page.layout(), (QVBoxLayout, QHBoxLayout, QGridLayout))
            margins = page.layout().contentsMargins()
            self.assertEqual(
                (margins.left(), margins.top(), margins.right(), margins.bottom()),
                enterprise_layout.PAGE_MARGINS,
            )
            self.assertEqual(page.layout().spacing(), enterprise_layout.PAGE_SPACING)

        for width, height in self.RESOLUTIONS:
            window.resize(width, height)
            self.app.processEvents()
            self.assertEqual(window.sidebar.width(), enterprise_layout.SIDEBAR_WIDTH)
            self.assertEqual(window.toolbar.height(), enterprise_layout.TOOLBAR_HEIGHT)
            self.assertEqual(window.status.height(), enterprise_layout.STATUSBAR_HEIGHT)
            self.assertGreaterEqual(window.stack.width(), width - enterprise_layout.SIDEBAR_WIDTH - 24)
            self.assertGreater(window.stack.height(), 0)
            for index, page in enumerate(pages):
                window.stack.setCurrentIndex(index)
                self.app.processEvents()
                self.assertEqual(page.size(), window.stack.size(), page.__class__.__name__)
                self.assertFalse(page.grab().isNull(), page.__class__.__name__)
        window.close()

    def test_shell_sources_have_no_absolute_positioning_or_splitters(self):
        root = Path(__file__).resolve().parents[1] / "dashboard"
        sources = [root / "main_window.py", *(root / "pages").glob("*.py")]
        content = "\n".join(path.read_text(encoding="utf-8") for path in sources)
        self.assertNotIn(".setGeometry(", content)
        self.assertNotIn(".move(", content)
        self.assertNotIn("QSplitter", content)
        self.assertNotIn("QFormLayout", content)


if __name__ == "__main__":
    unittest.main()
