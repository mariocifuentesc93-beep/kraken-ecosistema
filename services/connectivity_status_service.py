"""Read-only connectivity snapshots for the professional Qt interface."""

from dataclasses import dataclass


DISCONNECTED = "DISCONNECTED"
CONNECTING = "CONNECTING"
CONNECTED = "CONNECTED"
ERROR = "ERROR"

STATUS_LABELS = {
    DISCONNECTED: "Desconectado",
    CONNECTING: "Conectando",
    CONNECTED: "Conectado",
    ERROR: "Error",
}

STATUS_COLORS = {
    DISCONNECTED: "#7F8C8D",
    CONNECTING: "#FFC107",
    CONNECTED: "#00C853",
    ERROR: "#E53935",
}


@dataclass(frozen=True)
class ConnectivityStatus:
    service: str
    state: str
    account_name: str = ""
    identity: str = ""
    server: str = ""
    account_type: str = ""
    last_error: str = ""

    @property
    def label(self):
        return STATUS_LABELS[self.state]

    @property
    def color(self):
        return STATUS_COLORS[self.state]

    @property
    def connected(self):
        return self.state == CONNECTED

    @property
    def tooltip(self):
        lines = [f"{self.service}: {self.label}"]
        for value in (
            self.account_name,
            self.identity,
            self.server,
            self.account_type,
        ):
            if value:
                lines.append(value)
        if self.last_error:
            lines.append(f"Último error: {self.last_error}")
        return "\n".join(lines)


def _mask(value, visible=4):
    text = str(value or "").strip()
    if not text:
        return ""
    return ("*" * max(3, len(text) - visible)) + text[-visible:]


class ConnectivityStatusService:
    """Inspect existing clients/connectors without creating connections."""

    def __init__(
        self,
        mt5_connector_instance=None,
        telegram_manager_instance=None,
    ):
        self._mt5_connector = mt5_connector_instance
        self._telegram_manager = telegram_manager_instance

    def _mt5(self):
        if self._mt5_connector is None:
            from mt5.connector import mt5_connector

            self._mt5_connector = mt5_connector
        return self._mt5_connector

    def _telegram(self):
        if self._telegram_manager is None:
            from telegram.account_manager import telegram_account_manager

            self._telegram_manager = telegram_account_manager
        return self._telegram_manager

    def get_mt5_status(self):
        connector = self._mt5()
        account = getattr(connector, "account", None)
        account_info = None
        if getattr(connector, "connecting", False):
            state = CONNECTING
        else:
            try:
                connected = bool(connector.is_connected())
                account_info = (
                    connector.get_account_info() if connected else None
                )
                connected = connected and account_info is not None
            except Exception as error:
                connector.last_error = str(error)
                connected = False
            state = (
                CONNECTED
                if connected
                else ERROR
                if getattr(connector, "last_error", "")
                else DISCONNECTED
            )
        login = (
            getattr(account, "login", None)
            or getattr(connector, "current_account", None)
            or getattr(account_info, "login", None)
        )
        return ConnectivityStatus(
            service="MT5",
            state=state,
            account_name=getattr(account, "name", "") if account else "",
            identity=f"Cuenta: {_mask(login)}" if login else "",
            server=(
                getattr(account, "server", "")
                if account
                else getattr(account_info, "server", "")
            ),
            account_type=(
                getattr(account, "execution_mode", "")
                if account
                else str(getattr(account_info, "trade_mode", "") or "")
            ),
            last_error=getattr(connector, "last_error", ""),
        )

    def get_telegram_status(self, account_id=None):
        manager = self._telegram()
        account = (
            manager.get_account(account_id)
            if account_id is not None
            else manager.get_active_account()
        )
        state = manager.connection_state(
            getattr(account, "id", None)
        )
        identity = ""
        if account:
            username = str(getattr(account, "username", "") or "").strip()
            phone = str(getattr(account, "phone", "") or "").strip()
            identity = f"@{username}" if username else _mask(phone)
        return ConnectivityStatus(
            service="Telegram",
            state=state,
            account_name=(
                getattr(account, "display_name", "") if account else ""
            ),
            identity=identity,
            last_error=manager.last_error(
                getattr(account, "id", None)
            ),
        )


connectivity_status_service = ConnectivityStatusService()
