import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from dashboard.pages import telegram_accounts_page
from dashboard.pages.telegram_accounts_page import TelegramAccountsPage
from dashboard import main_window
from dashboard.main_window import MainWindow


def test_first_use_message_is_shown_only_without_accounts(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        telegram_accounts_page.telegram_account_manager,
        "reload",
        lambda: True,
    )
    monkeypatch.setattr(
        telegram_accounts_page.telegram_account_repository,
        "get_all",
        lambda: [],
    )

    page = TelegramAccountsPage()
    page.show()
    app.processEvents()

    assert page.table.rowCount() == 0
    assert page.summary.text() == (
        "No hay ninguna cuenta de Telegram configurada.\n\n"
        "Haz clic en Conectar para agregar una nueva cuenta."
    )
    page.close()


def test_dashboard_connect_opens_account_setup_when_no_account(monkeypatch):
    refreshed = []
    destinations = []
    fake_window = SimpleNamespace(
        telegramPage=SimpleNamespace(
            refresh=lambda: refreshed.append(True),
        ),
        navigate_to_page=lambda title: destinations.append(title),
    )
    monkeypatch.setattr(
        main_window.telegram_account_repository,
        "get_all",
        lambda: [],
    )

    MainWindow.toggle_connection(fake_window, "Telegram")

    assert refreshed == [True]
    assert destinations == ["Cuentas Telegram"]


def test_dashboard_connect_opens_authorization_for_pending_account(
    monkeypatch,
):
    refreshed = []
    destinations = []
    fake_window = SimpleNamespace(
        telegramPage=SimpleNamespace(
            refresh=lambda: refreshed.append(True),
        ),
        navigate_to_page=lambda title: destinations.append(title),
    )
    monkeypatch.setattr(
        main_window.telegram_account_repository,
        "get_all",
        lambda: [
            SimpleNamespace(enabled=True, authorized=False),
        ],
    )

    MainWindow.toggle_connection(fake_window, "Telegram")

    assert refreshed == [True]
    assert destinations == ["Cuentas Telegram"]
