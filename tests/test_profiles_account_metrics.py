import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from dashboard.pages.profiles_page import ProfilesPage
from services.dashboard_account_metrics_service import DashboardAccountMetrics


class FakeMetricsService:
    def __init__(self, snapshot):
        self.result = snapshot
        self.profiles = []

    def snapshot(self, profile):
        self.profiles.append(profile)
        return self.result


def profile():
    return SimpleNamespace(
        id=1,
        active=True,
        name="demo",
        execution_mode="DEMO",
        total_operations=0,
        winning_operations=0,
        losing_operations=0,
        win_rate=0.0,
        net_profit=0.0,
        risk_mode="PERCENT",
        risk_percent=5.0,
        default_mt5_account=1,
    )


def test_profiles_page_shows_live_metrics_for_linked_mt5_account(monkeypatch):
    QApplication.instance() or QApplication([])
    selected = profile()
    monkeypatch.setattr(
        "dashboard.pages.profiles_page.profile_repository.get_all",
        lambda: [selected],
    )
    service = FakeMetricsService(
        DashboardAccountMetrics(
            available=True,
            balance=10008.80,
            equity=10008.80,
            free_margin=9980.25,
            currency="USD",
        )
    )

    page = ProfilesPage(account_metrics_service=service)

    assert page.table.item(0, 4).text() == "9,980.25"
    assert page.table.item(0, 5).text() == "10,008.80"
    assert service.profiles == [selected]
    page.close()


def test_profiles_page_keeps_placeholders_without_matching_mt5_metrics(
    monkeypatch,
):
    QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        "dashboard.pages.profiles_page.profile_repository.get_all",
        lambda: [profile()],
    )

    page = ProfilesPage(
        account_metrics_service=FakeMetricsService(
            DashboardAccountMetrics()
        )
    )

    assert page.table.item(0, 4).text() == "-"
    assert page.table.item(0, 5).text() == "-"
    page.close()
