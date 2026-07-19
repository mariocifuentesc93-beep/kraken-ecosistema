from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
)

from repositories.profile_repository import profile_repository
from repositories.symbol_repository import symbol_repository


class SymbolsPage(QWidget):

    def __init__(self):

        super().__init__()

        self.build_ui()

        self.load_profiles()

        self.refresh()

    # ======================================================

    def build_ui(self):

        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()

        layout.addLayout(toolbar)

        toolbar.addWidget(QLabel("Perfil"))

        self.cbo_profile = QComboBox()

        self.cbo_profile.currentIndexChanged.connect(
            self.refresh
        )

        toolbar.addWidget(self.cbo_profile)

        self.btn_enable = QPushButton(
            "Activar"
        )

        self.btn_disable = QPushButton(
            "Desactivar"
        )

        self.btn_enable_all = QPushButton(
            "Activar Todos"
        )

        self.btn_disable_all = QPushButton(
            "Desactivar Todos"
        )

        self.btn_refresh = QPushButton(
            "Actualizar"
        )

        toolbar.addWidget(self.btn_enable)

        toolbar.addWidget(self.btn_disable)

        toolbar.addWidget(self.btn_enable_all)

        toolbar.addWidget(self.btn_disable_all)

        toolbar.addStretch()

        toolbar.addWidget(self.btn_refresh)

        self.table = QTableWidget()

        layout.addWidget(self.table)

        self.table.setColumnCount(7)

        self.table.setHorizontalHeaderLabels([

            "ID",
            "Símbolo",
            "Descripción",
            "Activo",
            "Spread",
            "Última actualización",
            "Perfil",

        ])

        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        self.table.setSelectionBehavior(
            QTableWidget.SelectRows
        )

        self.table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        self.table.setAlternatingRowColors(
            True
        )

        self.btn_refresh.clicked.connect(
            self.refresh
        )

        self.btn_enable.clicked.connect(
            self.enable_symbol
        )

        self.btn_disable.clicked.connect(
            self.disable_symbol
        )

        self.btn_enable_all.clicked.connect(
            self.enable_all
        )

        self.btn_disable_all.clicked.connect(
            self.disable_all
        )

    # ======================================================

    def load_profiles(self):

        self.cbo_profile.clear()

        profiles = profile_repository.get_all()

        for profile in profiles:

            self.cbo_profile.addItem(
                profile.name,
                profile.id,
            )

    # ======================================================

    def refresh(self):

        if self.cbo_profile.count() == 0:

            return

        profile_id = self.cbo_profile.currentData()

        symbols = symbol_repository.get_all(
            profile_id
        )

        self.table.setRowCount(
            len(symbols)
        )

        for row, symbol in enumerate(symbols):

            values = [

                symbol.id,

                symbol.symbol,

                getattr(
                    symbol,
                    "description",
                    "",
                ),

                "Sí" if symbol.enabled else "No",

                getattr(
                    symbol,
                    "spread",
                    "",
                ),

                getattr(
                    symbol,
                    "updated_at",
                    "",
                ),

                profile_id,

            ]

            for col, value in enumerate(values):

                item = QTableWidgetItem(
                    str(value)
                )

                item.setTextAlignment(
                    Qt.AlignCenter
                )

                self.table.setItem(
                    row,
                    col,
                    item,
                )

    # ======================================================

    def selected_symbol(self):

        row = self.table.currentRow()

        if row < 0:

            return None

        profile_id = self.cbo_profile.currentData()

        symbol = self.table.item(
            row,
            1,
        ).text()

        return symbol_repository.get_by_symbol(
            profile_id,
            symbol,
        )

    # ======================================================

    def enable_symbol(self):

        symbol = self.selected_symbol()

        if symbol is None:

            return

        symbol.enabled = True

        self._save_symbol(symbol)

        self.refresh()

    # ======================================================

    def disable_symbol(self):

        symbol = self.selected_symbol()

        if symbol is None:

            return

        symbol.enabled = False

        self._save_symbol(symbol)

        self.refresh()

    # ======================================================

    def enable_all(self):

        profile_id = self.cbo_profile.currentData()

        symbols = symbol_repository.get_all(
            profile_id
        )

        for symbol in symbols:

            symbol.enabled = True

            self._save_symbol(symbol)

        QMessageBox.information(

            self,

            "Símbolos",

            "Todos los símbolos fueron activados.",

        )

        self.refresh()

    # ======================================================

    def disable_all(self):

        profile_id = self.cbo_profile.currentData()

        symbols = symbol_repository.get_all(
            profile_id
        )

        for symbol in symbols:

            symbol.enabled = False

            self._save_symbol(symbol)

        QMessageBox.information(

            self,

            "Símbolos",

            "Todos los símbolos fueron desactivados.",

        )

        self.refresh()

    @staticmethod
    def _save_symbol(symbol):
        return symbol_repository.update(
            symbol.id,
            symbol.enabled,
            symbol.mt5_symbol,
            symbol.description,
            symbol.aliases,
            symbol.risk,
            symbol.min_lot,
            symbol.max_lot,
            symbol.action,
        )
