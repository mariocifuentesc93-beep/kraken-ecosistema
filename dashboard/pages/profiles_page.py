from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
)

from repositories.profile_repository import profile_repository
from dashboard.dialogs.profile_dialog import ProfileDialog


class ProfilesPage(QWidget):

    def __init__(self):

        super().__init__()

        self.build_ui()

        self.refresh()

    # ======================================================

    def build_ui(self):

        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()

        layout.addLayout(toolbar)

        self.btn_new = QPushButton("Nuevo")
        self.btn_edit = QPushButton("Editar")
        self.btn_delete = QPushButton("Eliminar")
        self.btn_activate = QPushButton("Activar")
        self.btn_refresh = QPushButton("Actualizar")

        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(self.btn_activate)

        toolbar.addStretch()

        toolbar.addWidget(self.btn_refresh)

        self.table = QTableWidget()

        layout.addWidget(self.table)

        self.table.setColumnCount(13)

        self.table.setHorizontalHeaderLabels(
            [
                "ID",
                "Activo",
                "Nombre",
                "Modo",
                "Capital",
                "Balance",
                "Operaciones",
                "Wins",
                "Losses",
                "Win Rate",
                "Profit",
                "Drawdown",
                "Riesgo",
            ]
        )

        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        self.table.setSelectionBehavior(
            QTableWidget.SelectRows
        )

        self.table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        self.table.setAlternatingRowColors(True)

        self.btn_new.clicked.connect(
            self.new_profile
        )

        self.btn_edit.clicked.connect(
            self.edit_profile
        )

        self.btn_delete.clicked.connect(
            self.delete_profile
        )

        self.btn_activate.clicked.connect(
            self.activate_profile
        )

        self.btn_refresh.clicked.connect(
            self.refresh
        )

    # ======================================================

    def refresh(self):

        profiles = profile_repository.get_all()

        self.table.setRowCount(len(profiles))

        for row, profile in enumerate(profiles):

            values = [

                profile.id,

                "✔" if profile.active else "",

                profile.name,

                profile.execution_mode,

                "-",

                "-",

                profile.total_operations,

                profile.winning_operations,

                profile.losing_operations,

                f"{profile.win_rate:.2f}%",

                f"{profile.net_profit:,.2f}",

                "0.00%",

                f"{profile.risk_mode} ({profile.risk_percent})",

            ]

            for column, value in enumerate(values):

                item = QTableWidgetItem(str(value))

                item.setTextAlignment(Qt.AlignCenter)

                self.table.setItem(
                    row,
                    column,
                    item,
                )

    # ======================================================

    def selected_profile(self):

        row = self.table.currentRow()

        if row < 0:

            return None

        profile_id = int(
            self.table.item(row, 0).text()
        )

        return profile_repository.get_by_id(
            profile_id
        )

    # ======================================================

    def new_profile(self):

        dialog = ProfileDialog(parent=self)

        if dialog.exec():

            self.refresh()

    # ======================================================

    def edit_profile(self):

        profile = self.selected_profile()

        if profile is None:

            QMessageBox.warning(

                self,

                "Perfil",

                "Seleccione un perfil.",

            )

            return

        dialog = ProfileDialog(profile=profile, parent=self)

        if hasattr(dialog, "load_profile"):

            dialog.load_profile(profile)

        if dialog.exec():

            self.refresh()

    # ======================================================

    def delete_profile(self):

        profile = self.selected_profile()

        if profile is None:

            QMessageBox.warning(

                self,

                "Perfil",

                "Seleccione un perfil.",

            )

            return

        reply = QMessageBox.question(

            self,

            "Eliminar perfil",

            f"¿Desea eliminar el perfil '{profile.name}'?",

            QMessageBox.Yes | QMessageBox.No,

        )

        if reply != QMessageBox.Yes:

            return

        profile_repository.delete(profile.id)

        self.refresh()

    # ======================================================

    def activate_profile(self):

        profile = self.selected_profile()

        if profile is None:

            QMessageBox.warning(

                self,

                "Perfil",

                "Seleccione un perfil.",

            )

            return

        profiles = profile_repository.get_all()

        for p in profiles:

            p.active = False
            p.enabled = True

            profile_repository.update(p)

        profile.active = True
        profile.enabled = True

        profile_repository.update(profile)

        self.refresh()

        QMessageBox.information(

            self,

            "Perfil",

            f"Perfil '{profile.name}' activado.",

        )