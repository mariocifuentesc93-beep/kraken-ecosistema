import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from dashboard.pages.channels_page import ChannelsPage


class Accounts:
    def get_all(self):
        return []

    def get_by_id(self, _account_id):
        return None


class Channels:
    def list_by_account(self, _account_id):
        return []

    def get_by_id(self, _channel_id):
        return None


def test_channels_page_is_global_catalog_without_profile_selector():
    app = QApplication.instance() or QApplication([])
    page = ChannelsPage(
        account_repository=Accounts(),
        channel_repository=Channels(),
        sync_service=object(),
    )

    assert hasattr(page, "account_combo")
    assert not hasattr(page, "profile_combo")
    assert page.table.columnCount() == 8
    assert "Perfil" not in [
        page.table.horizontalHeaderItem(index).text()
        for index in range(page.table.columnCount())
    ]
    assert "No hay ninguna cuenta" in page.status_label.text()
    page.deleteLater()
