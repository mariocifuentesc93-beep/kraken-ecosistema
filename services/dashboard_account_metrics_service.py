from dataclasses import dataclass


@dataclass(frozen=True)
class DashboardAccountMetrics:
    available: bool = False
    balance: float = 0.0
    equity: float = 0.0
    free_margin: float = 0.0
    currency: str = ""


class DashboardAccountMetricsService:
    """Read-only snapshot of the profile-scoped MT5 account."""

    def __init__(
        self,
        connector=None,
        account_provider=None,
        connection_registry=None,
    ):
        self._connector = connector
        self._account_provider = account_provider
        self._connection_registry = connection_registry
        # Explicit connector injection keeps legacy tests and callers isolated.
        self._prefer_registry = connector is None

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

    @property
    def connection_registry(self):
        if self._connection_registry is None:
            from services.mt5_connection_registry import (
                mt5_connection_registry,
            )

            self._connection_registry = mt5_connection_registry
        return self._connection_registry

    @staticmethod
    def _metrics(info):
        if info is None:
            return DashboardAccountMetrics()
        return DashboardAccountMetrics(
            available=True,
            balance=float(getattr(info, "balance", 0.0) or 0.0),
            equity=float(getattr(info, "equity", 0.0) or 0.0),
            free_margin=float(getattr(info, "margin_free", 0.0) or 0.0),
            currency=str(getattr(info, "currency", "") or ""),
        )

    @staticmethod
    def _login_matches(account, info):
        try:
            expected_login = int(account.login)
            detected_login = int(getattr(info, "login", 0) or 0)
        except (TypeError, ValueError):
            return False
        return expected_login > 0 and detected_login == expected_login

    def _profile_connection_info(self, profile):
        account_id = getattr(profile, "default_mt5_account", None)
        if account_id is None:
            return None, None
        account = self.account_provider(account_id)
        if account is None:
            return None, None
        terminal_id = (
            getattr(profile, "mt5_terminal_id", None)
            or getattr(account, "mt5_terminal_id", None)
        )
        if terminal_id is None:
            return account, None
        connection = self.connection_registry.peek(account.id, terminal_id)
        if connection is None or not connection.alive:
            return account, None
        try:
            return account, connection.account_info()
        except Exception:
            return account, None

    def snapshot(self, profile=None) -> DashboardAccountMetrics:
        default_account_id = getattr(profile, "default_mt5_account", None)

        if self._prefer_registry and default_account_id is not None:
            account, info = self._profile_connection_info(profile)
            if account is None or info is None:
                return DashboardAccountMetrics()
            if not self._login_matches(account, info):
                return DashboardAccountMetrics()
            return self._metrics(info)

        connector = self.connector
        if not connector.is_connected():
            return DashboardAccountMetrics()

        info = connector.get_account_info()
        if info is None:
            return DashboardAccountMetrics()

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

            if not self._login_matches(expected_account, info):
                return DashboardAccountMetrics()

        return self._metrics(info)


dashboard_account_metrics_service = DashboardAccountMetricsService()
