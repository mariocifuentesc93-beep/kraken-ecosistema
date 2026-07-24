import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QInputDialog

from dashboard.pages import telegram_accounts_page
from dashboard.pages.telegram_accounts_page import TelegramAccountsPage
from services.telegram_diagnostics import TelegramDiagnostics


class GuidedDiagnostics:
    CODE_REQUIRED = TelegramDiagnostics.CODE_REQUIRED
    PASSWORD_REQUIRED = TelegramDiagnostics.PASSWORD_REQUIRED

    def __init__(self, password_required=False):
        self.password_required = password_required
        self.calls = []

    async def start_authorization(self, account):
        self.calls.append(("start", account.id))
        return {
            "status": self.CODE_REQUIRED,
            "success": False,
        }

    async def verify_code(self, account, code, password=None):
        self.calls.append(("verify", account.id, code, password))
        if self.password_required and password is None:
            return {
                "status": self.PASSWORD_REQUIRED,
                "success": False,
            }
        return {
            "status": TelegramDiagnostics.AUTHORIZED,
            "success": True,
        }


def _page(monkeypatch, diagnostics):
    account = SimpleNamespace(
        id=7,
        connected=False,
        authorized=False,
        enabled=False,
        session_name="",
    )
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
    updates = []
    monkeypatch.setattr(
        telegram_accounts_page.telegram_account_repository,
        "update",
        lambda item: updates.append(item) or True,
    )
    monkeypatch.setattr(
        telegram_accounts_page,
        "telegram_diagnostics",
        diagnostics,
    )
    page = TelegramAccountsPage()
    monkeypatch.setattr(page, "selected_account", lambda: account)
    monkeypatch.setattr(page, "refresh", lambda: None)
    reports = []
    monkeypatch.setattr(page, "_show_diagnostic", reports.append)
    return page, reports, account, updates


def test_start_authorization_opens_code_dialog_automatically(monkeypatch):
    app = QApplication.instance() or QApplication([])
    diagnostics = GuidedDiagnostics()
    page, reports, account, updates = _page(monkeypatch, diagnostics)
    prompts = []

    def get_text(_parent, title, label, *_args):
        prompts.append((title, label))
        return "12345", True

    monkeypatch.setattr(QInputDialog, "getText", get_text)
    page.start_authorization()
    app.processEvents()

    assert prompts == [
        (
            "Autorización Telegram",
            "Introduzca el código recibido en Telegram",
        )
    ]
    assert diagnostics.calls == [
        ("start", 7),
        ("verify", 7, "12345", None),
    ]
    assert reports[-1]["status"] == TelegramDiagnostics.AUTHORIZED
    assert page.btn_start_auth.isEnabled() is True
    assert account.enabled is True
    assert account.session_name.startswith("sessions/telegram_")
    assert updates == [account]
    page.close()


def test_two_step_password_dialog_opens_automatically(monkeypatch):
    app = QApplication.instance() or QApplication([])
    diagnostics = GuidedDiagnostics(password_required=True)
    page, reports, _account, _updates = _page(monkeypatch, diagnostics)
    answers = iter((("12345", True), ("test-password", True)))
    prompts = []

    def get_text(_parent, title, label, *_args):
        prompts.append((title, label))
        return next(answers)

    monkeypatch.setattr(QInputDialog, "getText", get_text)
    page.start_authorization()
    app.processEvents()

    assert prompts == [
        (
            "Autorización Telegram",
            "Introduzca el código recibido en Telegram",
        ),
        (
            "Verificación en dos pasos",
            "Introduzca la contraseña de dos pasos de Telegram",
        ),
    ]
    assert diagnostics.calls[-1] == (
        "verify",
        7,
        "12345",
        "test-password",
    )
    assert reports[-1]["status"] == TelegramDiagnostics.AUTHORIZED
    page.close()
