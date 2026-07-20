import os
import shutil
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
)

from dashboard.professional_forms import professional_forms
from database.database_manager import database_manager


class ProfessionalFormsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.original = database_manager.database
        database_manager.close()
        self.directory = Path(tempfile.mkdtemp())
        database_manager.database = self.directory / "professional-forms.db"
        database_manager.initialize()

    def tearDown(self):
        database_manager.close()
        database_manager.database = self.original
        shutil.rmtree(self.directory)

    @staticmethod
    def pages(window):
        return (
            window.settingsPage,
            window.paperTradingPage,
            window.replayPage,
            window.telegramPage,
            window.mt5Page,
            window.profilesPage,
            window.tradingCalendarPage,
            window.analyticsPage,
        )

    def test_required_pages_use_the_complete_form_contract(self):
        from dashboard.main_window import MainWindow

        window = MainWindow()
        field_types = (QComboBox, QDateEdit, QDoubleSpinBox, QLineEdit, QSpinBox)
        for page in self.pages(window):
            self.assertTrue(page.property("professionalForm"), page.__class__.__name__)
            self.assertEqual(tuple(page.property("formRegions")), professional_forms.REGIONS)
            self.assertEqual(len(page.findChildren(QFrame, "EnterprisePageHeader")), 1)
            roles = {label.property("role") for label in page.findChildren(QLabel)}
            self.assertIn("pageTitle", roles)
            self.assertIn("subtitle", roles)
            for field_type in field_types:
                for field in page.findChildren(field_type):
                    self.assertEqual(field.property("formRegion"), "filters")
                    self.assertGreaterEqual(field.minimumWidth(), professional_forms.FIELD_MINIMUM_WIDTH)
            for button in page.findChildren(QPushButton):
                self.assertIn(button.property("formRegion"), ("toolbar", "actions"))
                self.assertGreaterEqual(button.minimumHeight(), professional_forms.BUTTON_HEIGHT)
        window.close()

    def test_forms_remain_inside_the_workspace_at_supported_sizes(self):
        from dashboard.main_window import MainWindow

        window = MainWindow()
        window.show()
        controls = (QComboBox, QDateEdit, QDoubleSpinBox, QLineEdit, QPushButton, QSpinBox)
        for width, height in ((1366, 768), (1600, 900), (1920, 1080), (2560, 1440), (3840, 2160)):
            window.resize(width, height)
            for page in self.pages(window):
                window.stack.setCurrentWidget(page)
                self.app.processEvents()
                for control_type in controls:
                    for control in page.findChildren(control_type):
                        if not control.isVisible():
                            continue
                        top_left = control.mapTo(page, control.rect().topLeft())
                        self.assertGreaterEqual(top_left.x(), 0, page.__class__.__name__)
                        self.assertLessEqual(top_left.x() + control.width(), page.width(), page.__class__.__name__)
        window.close()

    def test_form_pages_have_no_absolute_positioning(self):
        root = Path(__file__).resolve().parents[1] / "dashboard" / "pages"
        names = ("settings_page.py", "paper_trading_page.py", "replay_page.py",
                 "telegram_accounts_page.py", "mt5_accounts_page.py", "profiles_page.py",
                 "trading_calendar_page.py", "analytics_page.py")
        source = "\n".join((root / name).read_text(encoding="utf-8") for name in names)
        self.assertNotIn(".move(", source)
        self.assertNotIn(".setGeometry(", source)


if __name__ == "__main__":
    unittest.main()
