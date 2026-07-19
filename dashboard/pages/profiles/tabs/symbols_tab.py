from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QMessageBox,
)

from controllers.symbol_controller import symbol_controller
from dashboard.pages.profiles.symbol_dialog import SymbolDialog


class SymbolsTab(QWidget):

    def __init__(self):

        super().__init__()

        self.profile = None

        self.build_ui()

    # ---------------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        self.table = QTableWidget()

        self.table.setColumnCount(8)

        self.table.setHorizontalHeaderLabels([

            "Activo",

            "Símbolo",

            "Descripción",

            "Alias",

            "Riesgo",

            "Lote Min",

            "Lote Max",

            "Acción"

        ])

        layout.addWidget(self.table)

        buttons = QHBoxLayout()

        self.add = QPushButton("➕ Agregar")

        self.delete = QPushButton("🗑 Eliminar")

        self.refresh = QPushButton("🔄 Actualizar")

        buttons.addWidget(self.add)

        buttons.addWidget(self.delete)

        buttons.addStretch()

        buttons.addWidget(self.refresh)

        layout.addLayout(buttons)

        self.add.clicked.connect(self.add_symbol)

        self.delete.clicked.connect(self.delete_symbol)

        self.refresh.clicked.connect(self.reload)

    # ---------------------------------------------------------

    def load(self, profile):

        self.profile = profile

        self.reload()

    # ---------------------------------------------------------

    def reload(self):

        self.table.setRowCount(0)

        if self.profile is None:

            return

        symbols = symbol_controller.get_all(

            self.profile.id

        )

        self.table.setRowCount(

            len(symbols)

        )

        for row, symbol in enumerate(symbols):

            self.table.setItem(

                row,

                0,

                QTableWidgetItem(

                    "Sí" if symbol.enabled else "No"

                )

            )

            self.table.setItem(

                row,

                1,

                QTableWidgetItem(

                    symbol.symbol

                )

            )

            self.table.setItem(

                row,

                2,

                QTableWidgetItem(

                    symbol.description

                )

            )

            self.table.setItem(

                row,

                3,

                QTableWidgetItem(

                    symbol.aliases

                )

            )

            self.table.setItem(

                row,

                4,

                QTableWidgetItem(

                    str(symbol.risk)

                )

            )

            self.table.setItem(

                row,

                5,

                QTableWidgetItem(

                    str(symbol.min_lot)

                )

            )

            self.table.setItem(

                row,

                6,

                QTableWidgetItem(

                    str(symbol.max_lot)

                )

            )

            self.table.setItem(

                row,

                7,

                QTableWidgetItem(

                    symbol.action

                )

            )

            self.table.item(

                row,

                0

            ).setData(

                1000,

                symbol.id

            )

    # ---------------------------------------------------------

    def add_symbol(self):

        if self.profile is None:

            QMessageBox.warning(

                self,

                "Perfil",

                "Seleccione un perfil."

            )

            return

        dialog = SymbolDialog(self)

        if not dialog.exec():

            return

        data = dialog.get_data()

        symbol_controller.create(

            profile_id=self.profile.id,

            enabled=data["enabled"],

            symbol=data["symbol"],

            description=data["description"],

            aliases=data["aliases"],

            risk=data["risk"],

            min_lot=data["min_lot"],

            max_lot=data["max_lot"],

            action=data["action"],

        )

        self.reload()

    # ---------------------------------------------------------

    def delete_symbol(self):

        row = self.table.currentRow()

        if row < 0:

            return

        symbol_id = self.table.item(

            row,

            0

        ).data(

            1000

        )

        symbol_controller.delete(

            symbol_id

        )

        self.reload()