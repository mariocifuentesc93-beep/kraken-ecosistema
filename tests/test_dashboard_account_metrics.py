from types import SimpleNamespace

from services.dashboard_account_metrics_service import (
    DashboardAccountMetricsService,
)


class FakeConnector:
    def __init__(self, *, connected=True, account_id=1, info=None):
        self.connected = connected
        self.account = SimpleNamespace(id=account_id)
        self.info = info

    def is_connected(self):
        return self.connected

    def get_account_info(self):
        return self.info


def test_connected_mt5_snapshot_exposes_dashboard_balance_equity_and_capital():
    connector = FakeConnector(
        info=SimpleNamespace(
            balance=9995.60,
            equity=9995.60,
            margin_free=9875.25,
            currency="USD",
        )
    )
    snapshot = DashboardAccountMetricsService(connector).snapshot(
        SimpleNamespace(default_mt5_account=1)
    )

    assert snapshot.available is True
    assert snapshot.balance == 9995.60
    assert snapshot.equity == 9995.60
    assert snapshot.free_margin == 9875.25
    assert snapshot.currency == "USD"


def test_dashboard_does_not_show_an_account_not_assigned_to_selected_profile():
    connector = FakeConnector(
        account_id=1,
        info=SimpleNamespace(
            balance=9995.60,
            equity=9995.60,
            margin_free=9995.60,
            currency="USD",
        ),
    )
    snapshot = DashboardAccountMetricsService(connector).snapshot(
        SimpleNamespace(default_mt5_account=2)
    )

    assert snapshot.available is False


def test_disconnected_mt5_snapshot_is_unavailable():
    snapshot = DashboardAccountMetricsService(
        FakeConnector(connected=False)
    ).snapshot()

    assert snapshot.available is False


def test_profile_without_default_account_uses_the_connected_account():
    connector = FakeConnector(
        info=SimpleNamespace(
            balance=9995.60,
            equity=9995.60,
            margin_free=9995.60,
            currency="USD",
        )
    )
    snapshot = DashboardAccountMetricsService(
        connector
    ).snapshot(SimpleNamespace(default_mt5_account=None))

    assert snapshot.available is True
    assert snapshot.balance == 9995.60
