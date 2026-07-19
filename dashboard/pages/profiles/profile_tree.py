from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
)

from controllers.profile_controller import profile_controller


class ProfileTree(QWidget):

    profile_selected = Signal(object)

    def __init__(self):

        super().__init__()

        self.profiles = []

        self.build_ui()

    # ---------------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        self.list = QListWidget()

        self.list.itemSelectionChanged.connect(

            self.selection_changed

        )

        layout.addWidget(self.list)

        self.reload()

    # ---------------------------------------------------------

    def reload(self, selected_id=None):

        self.list.blockSignals(True)

        self.list.clear()

        self.profiles = profile_controller.get_all()

        row_to_select = None

        for row, profile in enumerate(self.profiles):

            icon = getattr(profile, "icon", "") or "📈"

            enabled = getattr(profile, "enabled", False)

            status = "🟢" if enabled else "🔴"

            item = QListWidgetItem(

                f"{status} {icon}  {profile.name}"

            )

            item.setData(

                Qt.UserRole,

                profile,

            )

            self.list.addItem(item)

            if (

                selected_id is not None

                and profile.id == selected_id

            ):

                row_to_select = row

        self.list.blockSignals(False)

        if self.list.count() == 0:

            return

        if row_to_select is None:

            row_to_select = 0

        self.list.setCurrentRow(row_to_select)

    # ---------------------------------------------------------

    def selection_changed(self):

        item = self.list.currentItem()

        if item is None:

            return

        profile = item.data(Qt.UserRole)

        if profile is None:

            return

        self.profile_selected.emit(profile)

    # ---------------------------------------------------------

    def current_profile(self):

        item = self.list.currentItem()

        if item is None:

            return None

        return item.data(Qt.UserRole)

    # ---------------------------------------------------------

    def select_profile(self, profile_id):

        for row in range(self.list.count()):

            item = self.list.item(row)

            profile = item.data(Qt.UserRole)

            if profile and profile.id == profile_id:

                self.list.setCurrentRow(row)

                return True

        return False

    # ---------------------------------------------------------

    def remove_selection(self):

        self.list.clearSelection()

    # ---------------------------------------------------------

    def count(self):

        return self.list.count()