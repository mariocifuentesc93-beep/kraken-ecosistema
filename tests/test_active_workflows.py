"""Offscreen smoke coverage for the repository-backed active dashboard."""

import shutil
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from core.config_service import load_active_config
from database.database_manager import database_manager
from engine.kraken_engine import kraken_engine
from models.profile import Profile
from repositories.profile_repository import profile_repository
from repositories.symbol_repository import symbol_repository
from repositories.mt5_account_repository import mt5_account_repository
from models.mt5_account import MT5Account


class ActiveWorkflowSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])
        cls._information = QMessageBox.information
        cls._question = QMessageBox.question
        QMessageBox.information = staticmethod(lambda *args: None)
        QMessageBox.question = staticmethod(lambda *args: QMessageBox.Yes)

    @classmethod
    def tearDownClass(cls):
        QMessageBox.information = cls._information
        QMessageBox.question = cls._question

    def setUp(self):
        self.original_database = database_manager.database
        database_manager.close()
        self.temporary_directory = Path(tempfile.mkdtemp())
        database_manager.database = self.temporary_directory / "workflow.db"
        database_manager.initialize()

    def tearDown(self):
        kraken_engine.stop()
        database_manager.close()
        database_manager.database = self.original_database
        shutil.rmtree(self.temporary_directory)

    def test_dashboard_profile_persistence_and_active_pages(self):
        from dashboard.dialogs.profile_dialog import ProfileDialog
        from dashboard.main_window import MainWindow

        window = MainWindow()
        self.assertEqual(window.stack.count(), 17)
        for index in range(window.stack.count()):
            window.menu.setCurrentRow(index)
            self.assertIs(window.stack.currentWidget(), window.stack.widget(index))

        dialog = ProfileDialog(parent=window)
        dialog.txtName.setText("Workflow Profile")
        dialog.cboExecution.setCurrentText("SIMULATION")
        dialog.save_profile()

        profile = profile_repository.get_all()[0]
        self.assertEqual(profile.name, "Workflow Profile")
        self.assertEqual(profile.execution_mode, "SIMULATION")

        edit_dialog = ProfileDialog(profile=profile, parent=window)
        edit_dialog.txtDescription.setPlainText("Persisted edit")
        edit_dialog.save_profile()
        database_manager.close()
        database_manager.initialize()
        self.assertEqual(profile_repository.get_by_id(profile.id).description, "Persisted edit")

        window.profilesPage.refresh()
        window.profilesPage.table.selectRow(0)
        window.profilesPage.activate_profile()
        self.assertEqual(profile_repository.get_active().id, profile.id)

        symbol_id = symbol_repository.create(
            profile.id, True, "EURUSD", "EURUSD", "", "", 1.0, 0.01, 100.0, "trade"
        )
        window.symbolsPage.load_profiles()
        window.symbolsPage.refresh()
        symbol_row = next(
            row for row in range(window.symbolsPage.table.rowCount())
            if window.symbolsPage.table.item(row, 1).text() == "EURUSD"
        )
        window.symbolsPage.table.selectRow(symbol_row)
        window.symbolsPage.disable_symbol()
        self.assertFalse(symbol_repository.get_by_id(symbol_id).enabled)

        mt5_account = MT5Account(
            name="Workflow MT5", login=123456, password="secret", server="Broker"
        )
        mt5_account_repository.create(mt5_account)
        window.mt5Page.refresh()
        self.assertEqual(window.mt5Page.table.rowCount(), 1)
        window.close()

    def test_database_backup_restore_integrity(self):
        profile_repository.create(Profile(name="Backup Profile"))
        database_manager.commit()
        backup = self.temporary_directory / "backup.db"
        restored = self.temporary_directory / "restored.db"
        database_manager.backup(backup)
        shutil.copy2(backup, restored)

        import sqlite3

        connection = sqlite3.connect(restored)
        try:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM profiles").fetchone()[0], 1)
        finally:
            connection.close()

    def test_main_window_backup_restore_and_simulation_actions(self):
        from dashboard.main_window import MainWindow

        profile_repository.create(
            Profile(name="Toolbar Simulation", execution_mode="SIMULATION")
        )
        self.assertTrue(load_active_config())
        window = MainWindow()
        backup = self.temporary_directory / "dashboard-backup.db"
        original_save = QFileDialog.getSaveFileName
        original_open = QFileDialog.getOpenFileName
        QFileDialog.getSaveFileName = staticmethod(lambda *args: (str(backup), ""))
        QFileDialog.getOpenFileName = staticmethod(lambda *args: (str(backup), ""))
        try:
            window.backup_database()
            self.assertTrue(backup.exists())
            profile_repository.create(Profile(name="Changed After Backup"))
            self.assertEqual(profile_repository.count(), 2)
            window.restore_database()
            self.assertEqual(profile_repository.count(), 1)

            window.actSimulation.trigger()
            self.assertEqual(window.mode, "SIMULATION")
            window.start_engine()
            self.assertEqual(kraken_engine.status.name, "RUNNING")
            window.stop_engine()
            self.assertEqual(kraken_engine.status.name, "STOPPED")
        finally:
            QFileDialog.getSaveFileName = original_save
            QFileDialog.getOpenFileName = original_open
            window.close()

    def test_simulation_engine_lifecycle(self):
        profile_repository.create(Profile(name="Simulation Profile", execution_mode="SIMULATION"))
        self.assertTrue(load_active_config())
        from dashboard.main_window import MainWindow

        window = MainWindow()
        window.set_mode("SIMULATION")
        kraken_engine.start()
        self.assertEqual(kraken_engine.status.name, "RUNNING")
        self.assertEqual(window.mode, "SIMULATION")
        kraken_engine.stop()
        self.assertEqual(kraken_engine.status.name, "STOPPED")
        self.assertEqual(window.mode, "OFF")
        window.close()


if __name__ == "__main__":
    unittest.main()
