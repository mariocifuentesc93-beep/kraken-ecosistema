from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QLineEdit,
    QMessageBox,
)

from dashboard.widgets.search_widget import SearchWidget
from dashboard.widgets.statistics_panel import StatisticsPanel


class ProfileManagerDialog(QDialog):

    createRequested = Signal()

    editRequested = Signal(object)

    deleteRequested = Signal(object)

    duplicateRequested = Signal(object)

    exportRequested = Signal(object)

    importRequested = Signal()

    activateRequested = Signal(object)

    compareRequested = Signal(list)

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Administrador de Perfiles")

        self.resize(1400, 900)

        self.profiles = []

        self.build_ui()

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QLineEdit,
    QMessageBox,
)

from dashboard.widgets.search_widget import SearchWidget
from dashboard.widgets.statistics_panel import StatisticsPanel


class ProfileManagerDialog(QDialog):

    createRequested = Signal()

    editRequested = Signal(object)

    deleteRequested = Signal(object)

    duplicateRequested = Signal(object)

    exportRequested = Signal(object)

    importRequested = Signal()

    activateRequested = Signal(object)

    compareRequested = Signal(list)

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Administrador de Perfiles")

        self.resize(1400, 900)

        self.profiles = []

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout(self)

        self.search = SearchWidget()

        layout.addWidget(self.search)

        self.table = QTableWidget()

        self.table.setColumnCount(9)

        self.table.setHorizontalHeaderLabels([

            "Activo",
            "Nombre",
            "Modo",
            "MT5",
            "Telegram",
            "Canales",
            "Símbolos",
            "Win %",
            "Profit"

        ])

        self.table.setSelectionBehavior(
            self.table.SelectRows
        )

        self.table.setSelectionMode(
            self.table.ExtendedSelection
        )

        self.table.setAlternatingRowColors(True)

        self.table.setSortingEnabled(True)

        layout.addWidget(self.table)

        self.statistics = StatisticsPanel()

        layout.addWidget(self.statistics)

        buttons = QHBoxLayout()

        layout.addLayout(buttons)

        self.btnNew = QPushButton("Nuevo")

        self.btnEdit = QPushButton("Editar")

        self.btnDelete = QPushButton("Eliminar")

        self.btnDuplicate = QPushButton("Duplicar")

        self.btnActivate = QPushButton("Activar")

        self.btnCompare = QPushButton("Comparar")

        self.btnExport = QPushButton("Exportar")

        self.btnImport = QPushButton("Importar")

        self.btnClose = QPushButton("Cerrar")

        for b in (

            self.btnNew,

            self.btnEdit,

            self.btnDelete,

            self.btnDuplicate,

            self.btnActivate,

            self.btnCompare,

            self.btnExport,

            self.btnImport,

        ):

            buttons.addWidget(b)

        buttons.addStretch()

        buttons.addWidget(self.btnClose)

        self.connect_signals()

    def connect_signals(self):

        self.btnClose.clicked.connect(
            self.close
        )

        self.search.searchChanged.connect(
            self.filter_profiles
        )

        self.btnNew.clicked.connect(
            self.createRequested.emit
        )

        self.btnEdit.clicked.connect(
            self.edit_profile
        )

        self.btnDelete.clicked.connect(
            self.delete_profile
        )

        self.btnDuplicate.clicked.connect(
            self.duplicate_profile
        )

        self.btnExport.clicked.connect(
            self.export_profile
        )

        self.btnImport.clicked.connect(
            self.importRequested.emit
        )

        self.btnActivate.clicked.connect(
            self.activate_profile
        )

        self.btnCompare.clicked.connect(
            self.compare_profiles
        )

    def load_profiles(self, profiles):

        self.profiles = profiles

        self.table.setRowCount(0)

        for profile in profiles:

            row = self.table.rowCount()

            self.table.insertRow(row)

            values = [

                "✔" if getattr(profile, "is_active", False) else "",

                getattr(profile, "name", ""),

                getattr(profile, "execution_mode", ""),

                len(getattr(profile, "mt5_accounts", [])),

                len(getattr(profile, "telegram_accounts", [])),

                len(getattr(profile, "channels", [])),

                len(getattr(profile, "symbols", [])),

                f'{getattr(profile, "win_rate", 0):.2f}%',

                f'{getattr(profile, "profit", 0):.2f}',

            ]

            for col, value in enumerate(values):

                item = QTableWidgetItem(str(value))

                item.setData(
                    Qt.UserRole,
                    profile
                )

                self.table.setItem(
                    row,
                    col,
                    item
                )

    def current_profile(self):

        row = self.table.currentRow()

        if row < 0:

            return None

        return self.table.item(
            row,
            0
        ).data(
            Qt.UserRole
        )

    def edit_profile(self):

        profile = self.current_profile()

        if profile:

            self.editRequested.emit(profile)

    def delete_profile(self):

        profile = self.current_profile()

        if profile:

            self.deleteRequested.emit(profile)

    def duplicate_profile(self):

        profile = self.current_profile()

        if profile:

            self.duplicateRequested.emit(profile)

    def export_profile(self):

        profile = self.current_profile()

        if profile:

            self.exportRequested.emit(profile)

    def activate_profile(self):

        profile = self.current_profile()

        if profile:

            self.activateRequested.emit(profile)

    def compare_profiles(self):

        profiles = []

        for index in self.table.selectionModel().selectedRows():

            item = self.table.item(
                index.row(),
                0
            )

            profiles.append(
                item.data(Qt.UserRole)
            )

        if len(profiles) < 2:

            QMessageBox.information(

                self,

                "Comparar",

                "Seleccione al menos dos perfiles."

            )

            return

        self.compareRequested.emit(
            profiles
        )

    def filter_profiles(self, text):

        text = text.lower()

        for row in range(self.table.rowCount()):

            visible = False

            for col in range(self.table.columnCount()):

                item = self.table.item(row, col)

                if item and text in item.text().lower():

                    visible = True

                    break

            self.table.setRowHidden(

                row,

                not visible

            )

    def set_statistics(self, stats):

        if not stats:

            self.statistics.clear()

            return

        for key, value in stats.items():

            self.statistics.setValue(
                key,
                value
            )

