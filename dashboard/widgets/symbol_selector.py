from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
)

from dashboard.widgets.search_widget import SearchWidget


class SymbolSelector(QWidget):

    selectionChanged = Signal()

    def __init__(self, parent=None):

        super().__init__(parent)

        layout = QVBoxLayout(self)

        self.search = SearchWidget()

        layout.addWidget(self.search)

        self.list = QListWidget()

        layout.addWidget(self.list)

        buttons = QHBoxLayout()

        self.btnAll = QPushButton(
            "Activar Todos"
        )

        self.btnNone = QPushButton(
            "Desactivar Todos"
        )

        buttons.addWidget(self.btnAll)

        buttons.addWidget(self.btnNone)

        layout.addLayout(buttons)

        self.search.searchChanged.connect(
            self.filter
        )

        self.btnAll.clicked.connect(
            self.selectAll
        )

        self.btnNone.clicked.connect(
            self.clearAll
        )

        self.list.itemChanged.connect(
            self.selectionChanged.emit
        )

    # ------------------------------------------------

    def loadSymbols(self, symbols):

        self.list.clear()

        for symbol in symbols:

            item = QListWidgetItem(
                symbol
            )

            item.setFlags(
                item.flags() | Qt.ItemIsUserCheckable
            )

            item.setCheckState(
                Qt.Unchecked
            )

            self.list.addItem(item)

    # ------------------------------------------------

    def filter(self, text):

        text = text.lower()

        for i in range(self.list.count()):

            item = self.list.item(i)

            item.setHidden(
                text not in item.text().lower()
            )

    # ------------------------------------------------

    def selectAll(self):

        for i in range(self.list.count()):

            self.list.item(i).setCheckState(
                Qt.Checked
            )

    # ------------------------------------------------

    def clearAll(self):

        for i in range(self.list.count()):

            self.list.item(i).setCheckState(
                Qt.Unchecked
            )

    # ------------------------------------------------

    def selectedSymbols(self):

        symbols = []

        for i in range(self.list.count()):

            item = self.list.item(i)

            if item.checkState() == Qt.Checked:

                symbols.append(
                    item.text()
                )

        return symbols

    # ------------------------------------------------

    def setSelected(self, symbols):

        symbols = set(symbols)

        for i in range(self.list.count()):

            item = self.list.item(i)

            item.setCheckState(

                Qt.Checked
                if item.text() in symbols
                else Qt.Unchecked

            )