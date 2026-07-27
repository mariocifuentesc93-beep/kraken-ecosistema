from dashboard.main_window import MainWindow


class _RefreshSpy:
    def __init__(self):
        self.calls = 0

    def refresh(self):
        self.calls += 1


class _FakeWindow:
    def __init__(self):
        self.dashboardPage = _RefreshSpy()
        self.connectivity_refreshes = 0
        self.logged = []

    def refresh_connectivity_status(self):
        self.connectivity_refreshes += 1

    def log(self, message):
        self.logged.append(message)


def test_successful_mt5_connection_refreshes_dashboard_metrics():
    window = _FakeWindow()

    MainWindow._connection_finished(window, "MT5", True, "")

    assert window.connectivity_refreshes == 1
    assert window.dashboardPage.calls == 1
    assert window.logged == []


def test_telegram_connection_does_not_refresh_mt5_dashboard_metrics():
    window = _FakeWindow()

    MainWindow._connection_finished(window, "Telegram", True, "")

    assert window.connectivity_refreshes == 1
    assert window.dashboardPage.calls == 0
