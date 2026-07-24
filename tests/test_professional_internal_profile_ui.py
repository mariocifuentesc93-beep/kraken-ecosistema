import os
import shutil
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from dashboard.dialogs.profile_dialog import ProfileDialog
from database.database_manager import database_manager
from models.profile import Profile


def test_professional_profile_dialog_exposes_internal_controls():
    app = QApplication.instance() or QApplication([])
    original_database = database_manager.database
    database_manager.close()
    directory = Path(tempfile.mkdtemp())
    database_manager.database = directory / "profile-ui.db"
    database_manager.initialize()

    try:
        profile = Profile(
            name="Internal profile",
            signal_source_mode="BOTH",
            publish_internal_to_telegram=True,
        )
        dialog = ProfileDialog(profile)
        dialog.show()
        app.processEvents()

        data = dialog.get_profile_data()

        assert dialog.cboSignalSource.currentText() == "BOTH"
        assert dialog.chkPublishInternal.isChecked() is True
        assert data["signal_source_mode"] == "BOTH"
        assert data["publish_internal_to_telegram"] is True
        assert data["execution_mode"] == "OFF"
        dialog.close()
    finally:
        database_manager.close()
        database_manager.database = original_database
        shutil.rmtree(directory)
