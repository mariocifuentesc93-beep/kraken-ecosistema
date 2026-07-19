"""Minimal process-safe Qt startup and shutdown smoke test."""

import unittest

from PySide6.QtWidgets import QApplication

from dashboard.main_window import MainWindow
from dashboard.dialogs.about_dialog import AboutDialog
from engine.kraken_engine import kraken_engine
from version import VERSION


class StartupShutdownSmokeTest(unittest.TestCase):
    def test_window_startup_and_shutdown(self):
        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        window.show()
        app.processEvents()
        self.assertIn(VERSION, window.lblVersion.text())
        about = AboutDialog(window)
        self.assertIn(VERSION, " ".join(label.text() for label in about.findChildren(type(window.lblVersion))))
        about.close()
        window.close()
        app.processEvents()
        self.assertEqual(kraken_engine.status.name, "STOPPED")


if __name__ == "__main__":
    unittest.main()
