from dataclasses import dataclass


@dataclass(frozen=True)
class DashboardAccountMetrics:
    available: bool = False
    balance: float = 0.0
    equity: float = 0.0
    free_margin: float = 0.0
    currency: str = ""


class DashboardAccountMetricsService:
    """Read-only snapshot of the MT5 account already connected by Kraken."""

    def __init__(self, connector=None, account_provider=None):
        self._connector = connector
        self._account_provider = account_provider

    @property
    def connector(self):
        if self._connector is None:
            from mt5.connector import mt5_connector

            self._connector = mt5_connector
        return self._connector

    @property
    def account_provider(self):
        if self._account_provider is None:
            from repositories.mt5_account_repository import (
                mt5_account_repository,
            )

            self._account_provider = mt5_account_repository.get_by_id
        return self._account_provider

    def snapshot(self, profile=None) -> DashboardAccountMetrics:
        connector = self.connector
        if not connector.is_connected():
            return DashboardAccountMetrics()

        info = connector.get_account_info()
        if info is None:
            return DashboardAccountMetrics()

        default_account_id = getattr(profile, "default_mt5_account", None)
        connected_account = getattr(connector, "account", None)
        if default_account_id is not None:
            expected_account = self.account_provider(default_account_id)
            if expected_account is None:
                return DashboardAccountMetrics()

            connected_account_id = getattr(connected_account, "id", None)
            if (
                connected_account_id is not None
                and connected_account_id != default_account_id
            ):
                return DashboardAccountMetrics()

            try:
                expected_login = int(expected_account.login)
                detected_login = int(getattr(info, "login", 0) or 0)
            except (TypeError, ValueError):
                return DashboardAccountMetrics()
            if expected_login <= 0 or detected_login != expected_login:
                return DashboardAccountMetrics()

        return DashboardAccountMetrics(
            available=True,
            balance=float(getattr(info, "balance", 0.0) or 0.0),
            equity=float(getattr(info, "equity", 0.0) or 0.0),
            free_margin=float(getattr(info, "margin_free", 0.0) or 0.0),
            currency=str(getattr(info, "currency", "") or ""),
        )


dashboard_account_metrics_service = DashboardAccountMetricsService()
