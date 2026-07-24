from types import SimpleNamespace

import pytest
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

from dashboard.widgets.connection_indicator import ConnectionIndicator
from services.connectivity_status_service import (
    CONNECTED,
    CONNECTING,
    DISCONNECTED,
    ERROR,
    ConnectivityStatusService,
)


class FakeMT5Connector:
    def __init__(self, state):
        self.connecting = state == CONNECTING
        self.connected = state == CONNECTED
        self.last_error = "terminal caído" if state == ERROR else ""
        self.current_account = 12345678
        self.account = SimpleNamespace(
            name="Kraken MT5",
            login=12345678,
            server="Broker-Demo",
            execution_mode="OFF",
        )

    def is_connected(self):
        return self.connected

    def get_account_info(self):
        return object() if self.connected else None


class FakeTelegramManager:
    def __init__(self, state):
        self.state = state
        self.account = SimpleNamespace(
            id=7,
            display_name="Cuenta Kraken",
            username="kraken_user",
            phone="+573001234567",
        )

    def get_active_account(self):
        return self.account

    def get_account(self, account_id):
        return self.account if account_id == 7 else None

    def connection_state(self, account_id=None):
        return self.state

    def last_error(self, account_id=None):
        return "sesión inválida" if self.state == ERROR else ""


@pytest.mark.parametrize(
    ("state", "label", "color"),
    [
        (DISCONNECTED, "Desconectado", "#7F8C8D"),
        (CONNECTING, "Conectando", "#FFC107"),
        (CONNECTED, "Conectado", "#00C853"),
        (ERROR, "Error", "#E53935"),
    ],
)
def test_mt5_real_states_are_mapped(state, label, color):
    service = ConnectivityStatusService(
        mt5_connector_instance=FakeMT5Connector(state),
        telegram_manager_instance=FakeTelegramManager(DISCONNECTED),
    )
    status = service.get_mt5_status()
    assert status.state == state
    assert status.label == label
    assert status.color == color
    assert "Cuenta:" in status.tooltip
    assert "12345678" not in status.tooltip


@pytest.mark.parametrize(
    ("state", "label", "color"),
    [
        (DISCONNECTED, "Desconectado", "#7F8C8D"),
        (CONNECTING, "Conectando", "#FFC107"),
        (CONNECTED, "Conectado", "#00C853"),
        (ERROR, "Error", "#E53935"),
    ],
)
def test_telegram_real_states_are_mapped(state, label, color):
    service = ConnectivityStatusService(
        mt5_connector_instance=FakeMT5Connector(DISCONNECTED),
        telegram_manager_instance=FakeTelegramManager(state),
    )
    status = service.get_telegram_status(7)
    assert status.state == state
    assert status.label == label
    assert status.color == color
    assert "@kraken_user" in status.tooltip


@pytest.mark.parametrize(
    ("state", "button", "enabled"),
    [
        (DISCONNECTED, "Conectar", True),
        (CONNECTING, "Conectando...", False),
        (CONNECTED, "Desconectar", True),
        (ERROR, "Reintentar", True),
    ],
)
def test_connection_button_tracks_state(state, button, enabled):
    application = QApplication.instance() or QApplication([])
    indicator = ConnectionIndicator("Telegram")
    indicator.setConnectionState(state)
    assert indicator.btnTest.text() == button
    assert indicator.btnTest.isEnabled() is enabled
    assert indicator.thread() is QThread.currentThread()
    indicator.close()

