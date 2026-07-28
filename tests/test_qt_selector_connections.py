"""Focused regression tests for argument-safe Qt selector connections."""

import os
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from dashboard.dialogs.profile_dialog import ProfileDialog
from dashboard.widgets.account_selector import AccountSelector
from dashboard.widgets.symbol_selector import SymbolSelector
from dashboard.widgets.telegram_selector import TelegramSelector
from database.database_manager import database_manager


def _application():
    return QApplication.instance() or QApplication([])


def test_argument_free_selection_signal_adapts_qt_item_argument(capsys):
    _application()
    account = SimpleNamespace(id=1, name="MT5 Demo")
    telegram = SimpleNamespace(id=2, name="Telegram Demo")

    for selector, values, selected in (
        (AccountSelector(), [account], [1]),
        (TelegramSelector(), [telegram], [2]),
        (SymbolSelector(), ["EmasVol20"], ["EmasVol20"]),
    ):
        emissions = []
        selector.selectionChanged.connect(lambda: emissions.append(True))

        loader = getattr(
            selector,
            "loadSymbols",
            getattr(selector, "loadAccounts", None),
        )
        for _ in range(3):
            loader(values)
            selector.setSelected(selected)

        # Programmatic reloads are quiet; a user check emits exactly once.
        assert emissions == []
        selector.list.item(0).setCheckState(Qt.Unchecked)
        assert emissions == [True]

    assert "Traceback" not in capsys.readouterr().err


def test_profile_dialog_selectors_open_reload_and_close_repeatedly():
    _application()
    original_database = database_manager.database
    database_manager.close()
    directory = Path(tempfile.mkdtemp())
    database_manager.database = directory / "qt-selectors.db"
    try:
        database_manager.initialize()
        for _ in range(3):
            dialog = ProfileDialog()
            dialog.load_repository_data()
            dialog._load_telegram_channels(0)
            assert not hasattr(dialog, "chkPublishInternal")
            assert not hasattr(dialog, "cboTelegramOutputAccount")
            assert not hasattr(dialog, "cboTelegramOutputChannel")
            dialog.close()
    finally:
        database_manager.close()
        database_manager.database = original_database
        shutil.rmtree(directory)


def test_profile_dialog_auto_selects_only_account_for_terminal():
    _application()
    original_database = database_manager.database
    database_manager.close()
    directory = Path(tempfile.mkdtemp())
    database_manager.database = directory / "profile-account.db"
    try:
        database_manager.initialize()
        dialog = ProfileDialog()
        account = SimpleNamespace(
            id=3,
            name="Copy general",
            mt5_terminal_id=11,
            balance=1500.0,
            connected=True,
        )
        dialog._all_mt5_accounts = [account]
        dialog.mt5TerminalCombo.clear()
        dialog.mt5TerminalCombo.addItem("Terminal general", 11)

        dialog._filter_mt5_accounts()

        assert dialog.get_profile_data()["default_mt5_account"] == 3
        assert "1 cuenta(s)" in dialog.lblMt5Capital.text()
        dialog.close()
    finally:
        database_manager.close()
        database_manager.database = original_database
        shutil.rmtree(directory)
