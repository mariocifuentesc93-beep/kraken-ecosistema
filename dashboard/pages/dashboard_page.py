from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QGridLayout,
    QVBoxLayout,
    QGroupBox,
)

from repositories.profile_repository import profile_repository
from repositories.operation_repository import operation_repository

from core.event_bus import event_bus


class DashboardPage(QWidget):

    def __init__(self):

        super().__init__()

        self.build_ui()

        self.connect_events()

        self.refresh()

    # =====================================================
    # EVENTOS
    # =====================================================

    def connect_events(self):

        event_bus.dashboardRefreshRequested.connect(

            self.refresh

        )

        event_bus.statisticsUpdated.connect(

            self.refresh

        )

        event_bus.profitUpdated.connect(

            self.refresh

        )

        event_bus.operationCreated.connect(

            self.refresh

        )

        event_bus.operationOpened.connect(

            self.refresh

        )

        event_bus.operationClosed.connect(

            self.refresh

        )

        event_bus.profileFinished.connect(

            self.refresh

        )

    # =====================================================
    # UI
    # =====================================================

    def build_ui(self):

        layout = QVBoxLayout(self)

        summary = QGroupBox("Resumen")

        layout.addWidget(summary)

        grid = QGridLayout(summary)

        self.lbl_mode = QLabel("-")
        self.lbl_profile = QLabel("-")
        self.lbl_capital = QLabel("-")
        self.lbl_balance = QLabel("-")
        self.lbl_profit = QLabel("-")
        self.lbl_operations = QLabel("-")
        self.lbl_open = QLabel("-")
        self.lbl_winrate = QLabel("-")
        self.lbl_wins = QLabel("-")
        self.lbl_losses = QLabel("-")
        self.lbl_drawdown = QLabel("-")
        self.lbl_status = QLabel("Activo")

        cards = [

            ("Modo", self.lbl_mode),
            ("Perfil", self.lbl_profile),
            ("Capital", self.lbl_capital),
            ("Balance", self.lbl_balance),
            ("Ganancia", self.lbl_profit),
            ("Operaciones", self.lbl_operations),
            ("Abiertas", self.lbl_open),
            ("Win Rate", self.lbl_winrate),
            ("Ganadas", self.lbl_wins),
            ("Perdidas", self.lbl_losses),
            ("Drawdown", self.lbl_drawdown),
            ("Estado", self.lbl_status),

        ]

        row = 0
        col = 0

        for title, label in cards:

            title_label = QLabel(title)

            title_label.setAlignment(Qt.AlignCenter)

            label.setAlignment(Qt.AlignCenter)

            grid.addWidget(title_label, row, col)

            grid.addWidget(label, row + 1, col)

            col += 1

            if col == 4:

                col = 0
                row += 2

    # =====================================================
    # REFRESH
    # =====================================================

    def refresh(self, *args):

        profiles = profile_repository.get_all()

        active = None

        for profile in profiles:

            if getattr(profile, "is_active", False):

                active = profile

                break

        if active is None:

            self.lbl_status.setText("Sin perfil activo")
            return

        operations = operation_repository.get_by_profile(

            active.id

        )

        open_operations = [

            op

            for op in operations

            if op.status in ("OPEN", "RUNNING")

        ]

        self.lbl_mode.setText(

            str(active.execution_mode)

        )

        self.lbl_profile.setText(

            active.name

        )

        self.lbl_capital.setText(

            f"${active.initial_balance:,.2f}"

        )

        self.lbl_balance.setText(

            f"${active.current_balance:,.2f}"

        )

        self.lbl_profit.setText(

            f"${active.total_profit:,.2f}"

        )

        self.lbl_operations.setText(

            str(active.total_operations)

        )

        self.lbl_open.setText(

            str(len(open_operations))

        )

        self.lbl_winrate.setText(

            f"{active.win_rate:.2f}%"

        )

        self.lbl_wins.setText(

            str(active.total_wins)

        )

        self.lbl_losses.setText(

            str(active.total_losses)

        )

        self.lbl_drawdown.setText(

            f"{active.max_drawdown:.2f}%"

        )

        self.lbl_status.setText(

            "En ejecución"

        )