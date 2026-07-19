"""Minimal process-safe Qt startup and shutdown smoke test."""

import unittest

from PySide6.QtWidgets import QApplication

from dashboard.main_window import MainWindow
from engine.kraken_engine import kraken_engine


class StartupShutdownSmokeTest(unittest.TestCase):
    def test_window_startup_and_shutdown(self):
        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        window.show()
        app.processEvents()
        window.close()
        app.processEvents()
        self.assertEqual(kraken_engine.status.name, "STOPPED")


if __name__ == "__main__":
    unittest.main()
