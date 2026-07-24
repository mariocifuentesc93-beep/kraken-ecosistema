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

    def __init__(self, connector=None):
        self._connector = connector

    @property
    def connector(self):
        if self._connector is None:
            from mt5.connector import mt5_connector

            self._connector = mt5_connector
        return self._connector

    def snapshot(self, profile=None) -> DashboardAccountMetrics:
        connector = self.connector
        if not connector.is_connected():
            return DashboardAccountMetrics()

        default_account_id = getattr(profile, "default_mt5_account", None)
        connected_account = getattr(connector, "account", None)
        if default_account_id is not None:
            if (
                connected_account is None
                or getattr(connected_account, "id", None) != default_account_id
            ):
                return DashboardAccountMetrics()

        info = connector.get_account_info()
        if info is None:
            return DashboardAccountMetrics()

        return DashboardAccountMetrics(
            available=True,
            balance=float(getattr(info, "balance", 0.0) or 0.0),
            equity=float(getattr(info, "equity", 0.0) or 0.0),
            free_margin=float(getattr(info, "margin_free", 0.0) or 0.0),
            currency=str(getattr(info, "currency", "") or ""),
        )


dashboard_account_metrics_service = DashboardAccountMetricsService()
