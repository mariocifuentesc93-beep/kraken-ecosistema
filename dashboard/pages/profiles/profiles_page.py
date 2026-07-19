from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QTabWidget,
    QMessageBox,
)

from controllers.profile_controller import profile_controller

from dashboard.pages.profiles.profile_tree import ProfileTree
from dashboard.pages.profiles.profile_dialog import ProfileDialog

from dashboard.pages.profiles.widgets.profile_toolbar import ProfileToolbar
from dashboard.pages.profiles.widgets.profile_header import ProfileHeader
from dashboard.pages.profiles.widgets.profile_summary import ProfileSummary

from dashboard.pages.profiles.tabs.general_tab import GeneralTab
from dashboard.pages.profiles.tabs.telegram_tab import TelegramTab
from dashboard.pages.profiles.tabs.mt5_tab import MT5Tab
from dashboard.pages.profiles.tabs.risk_tab import RiskTab
from dashboard.pages.profiles.tabs.trading_tab import TradingTab
from dashboard.pages.profiles.tabs.symbols_tab import SymbolsTab
from dashboard.pages.profiles.tabs.schedule_tab import ScheduleTab
from dashboard.pages.profiles.tabs.goals_tab import GoalsTab
from dashboard.pages.profiles.tabs.statistics_tab import StatisticsTab
from dashboard.pages.profiles.tabs.notes_tab import NotesTab


class ProfilesPage(QWidget):

    def __init__(self):

        super().__init__()

        self.current_profile = None

        self.build_ui()

        self.connect_events()

    # ---------------------------------------------------------

    def build_ui(self):

        root = QHBoxLayout(self)

        # =====================================================
        # PANEL IZQUIERDO
        # =====================================================

        left = QVBoxLayout()

        title = QLabel("Perfiles")

        title.setStyleSheet("""
            font-size:20px;
            font-weight:bold;
        """)

        self.tree = ProfileTree()

        left.addWidget(title)

        left.addWidget(self.tree)

        root.addLayout(left, 1)

        # =====================================================
        # PANEL DERECHO
        # =====================================================

        right = QVBoxLayout()

        self.toolbar = ProfileToolbar()

        self.header = ProfileHeader()

        self.summary = ProfileSummary()

        self.tabs = QTabWidget()

        self.general = GeneralTab()
        self.telegram = TelegramTab()
        self.mt5 = MT5Tab()
        self.risk = RiskTab()
        self.trading = TradingTab()
        self.symbols = SymbolsTab()
        self.schedule = ScheduleTab()
        self.goals = GoalsTab()
        self.statistics = StatisticsTab()
        self.notes = NotesTab()

        self.tab_widgets = [

            ("General", self.general),
            ("Telegram", self.telegram),
            ("MT5", self.mt5),
            ("Riesgo", self.risk),
            ("Trading", self.trading),
            ("Símbolos", self.symbols),
            ("Horario", self.schedule),
            ("Objetivos", self.goals),
            ("Estadísticas", self.statistics),
            ("Notas", self.notes),

        ]

        for name, widget in self.tab_widgets:

            self.tabs.addTab(widget, name)

        right.addWidget(self.toolbar)

        right.addWidget(self.header)

        right.addWidget(self.summary)

        right.addWidget(self.tabs)

        root.addLayout(right, 3)

    # ---------------------------------------------------------

    def connect_events(self):

        self.tree.profile_selected.connect(
            self.profile_changed
        )

        self.toolbar.new_clicked.connect(
            self.new_profile
        )

        self.toolbar.edit_clicked.connect(
            self.edit_profile
        )

        self.toolbar.duplicate_clicked.connect(
            self.duplicate_profile
        )

        self.toolbar.delete_clicked.connect(
            self.delete_profile
        )

        self.toolbar.activate_clicked.connect(
            self.activate_profile
        )

        self.toolbar.deactivate_clicked.connect(
            self.deactivate_profile
        )

        self.toolbar.refresh_clicked.connect(
            self.tree.reload
        )

    # ---------------------------------------------------------

    def profile_changed(self, profile):

        self.current_profile = profile

        self.header.set_profile(profile)

        self.summary.load(profile)

        for _, widget in self.tab_widgets:

            if hasattr(widget, "load"):

                widget.load(profile)

    # ---------------------------------------------------------

    def refresh_profile(self):

        if self.current_profile is None:

            self.tree.reload()

            return

        profile = profile_controller.get(
            self.current_profile.id
        )

        self.tree.reload()

        if profile:

            self.profile_changed(profile)

    # ---------------------------------------------------------

    def new_profile(self):

        dialog = ProfileDialog(parent=self)

        if not dialog.exec():

            return

        data = dialog.get_data()

        profile_controller.create(

            name=data["name"],
            description=data["description"],
            color=data["color"],
            icon=data["icon"],
            active=data["active"],
            operation_mode=data["operation_mode"],

        )

        self.refresh_profile()

    # ---------------------------------------------------------

    def edit_profile(self):

        if self.current_profile is None:

            return

        dialog = ProfileDialog(

            self.current_profile,

            self,

        )

        if not dialog.exec():

            return

        data = dialog.get_data()

        self.current_profile.name = data["name"]
        self.current_profile.description = data["description"]
        self.current_profile.color = data["color"]
        self.current_profile.icon = data["icon"]
        self.current_profile.active = data["active"]
        self.current_profile.operation_mode = data["operation_mode"]

        profile_controller.update(

            self.current_profile

        )

        self.refresh_profile()

    # ---------------------------------------------------------

    def duplicate_profile(self):

        if self.current_profile is None:

            return

        profile_controller.duplicate(

            self.current_profile.id

        )

        self.refresh_profile()

    # ---------------------------------------------------------

    def delete_profile(self):

        if self.current_profile is None:

            return

        result = QMessageBox.question(

            self,

            "Eliminar perfil",

            f"¿Eliminar el perfil '{self.current_profile.name}'?"

        )

        if result != QMessageBox.Yes:

            return

        profile_controller.delete(

            self.current_profile.id

        )

        self.current_profile = None

        self.tree.reload()

    # ---------------------------------------------------------

    def activate_profile(self):

        if self.current_profile is None:

            return

        profile_controller.activate(

            self.current_profile.id

        )

        self.refresh_profile()

    # ---------------------------------------------------------

    def deactivate_profile(self):

        if self.current_profile is None:

            return

        profile_controller.deactivate(

            self.current_profile.id

        )

        self.refresh_profile()