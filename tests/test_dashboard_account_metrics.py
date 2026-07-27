from types import SimpleNamespace

from services.dashboard_account_metrics_service import (
    DashboardAccountMetricsService,
)


class FakeConnector:
    def __init__(self, *, connected=True, account_id=1, info=None):
        self.connected = connected
        self.account = (
            SimpleNamespace(id=account_id)
            if account_id is not None
            else None
        )
        self.info = info

    def is_connected(self):
        return self.connected

    def get_account_info(self):
        return self.info


def test_connected_mt5_snapshot_exposes_dashboard_balance_equity_and_capital():
    connector = FakeConnector(
        info=SimpleNamespace(
            login=243274,
            balance=9995.60,
            equity=9995.60,
            margin_free=9875.25,
            currency="USD",
        )
    )
    snapshot = DashboardAccountMetricsService(
        connector,
        account_provider=lambda account_id: SimpleNamespace(
            id=account_id,
            login=243274,
        ),
    ).snapshot(
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
            login=243274,
            balance=9995.60,
            equity=9995.60,
            margin_free=9995.60,
            currency="USD",
        ),
    )
    snapshot = DashboardAccountMetricsService(
        connector,
        account_provider=lambda account_id: SimpleNamespace(
            id=account_id,
            login=999999,
        ),
    ).snapshot(
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
            login=243274,
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


def test_profile_metrics_use_matching_detected_login_when_connector_has_no_account():
    connector = FakeConnector(
        account_id=None,
        info=SimpleNamespace(
            login=243274,
            balance=10025.50,
            equity=10020.25,
            margin_free=9980.75,
            currency="USD",
        ),
    )
    service = DashboardAccountMetricsService(
        connector,
        account_provider=lambda account_id: SimpleNamespace(
            id=account_id,
            login=243274,
        ),
    )

    snapshot = service.snapshot(
        SimpleNamespace(default_mt5_account=1)
    )

    assert snapshot.available is True
    assert snapshot.balance == 10025.50
    assert snapshot.equity == 10020.25
    assert snapshot.free_margin == 9980.75


def test_profile_metrics_reject_different_detected_login():
    connector = FakeConnector(
        account_id=None,
        info=SimpleNamespace(
            login=7911007,
            balance=9995.60,
            equity=9995.60,
            margin_free=9995.60,
            currency="USD",
        ),
    )
    service = DashboardAccountMetricsService(
        connector,
        account_provider=lambda account_id: SimpleNamespace(
            id=account_id,
            login=243274,
        ),
    )

    snapshot = service.snapshot(
        SimpleNamespace(default_mt5_account=1)
    )

    assert snapshot.available is False
