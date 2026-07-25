from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
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

        self.catalog = QComboBox()
        self.catalog.addItem("Todos", None)
        self.catalog.addItem("Bridge Markets", "BRIDGE_SYNTHETICS")
        self.catalog.addItem("Weltrade", "WELTRADE_SYNTHETICS")
        layout.addWidget(self.catalog)

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
        self.catalog.currentIndexChanged.connect(self._apply_filters)

        self.btnAll.clicked.connect(
            self.selectAll
        )

        self.btnNone.clicked.connect(
            self.clearAll
        )

        self.list.itemChanged.connect(
            self._emit_selection_changed
        )

    def _emit_selection_changed(self, _item=None):
        """Adapt QListWidget.itemChanged(item) to our argument-free signal."""
        self.selectionChanged.emit()

    # ------------------------------------------------

    def loadSymbols(self, symbols):
        definitions = [
            {
                "canonical_name": getattr(symbol, "symbol", symbol),
                "display_name": getattr(symbol, "symbol", symbol),
                "catalog": None,
                "category": "",
            }
            for symbol in symbols
        ]
        self.loadCatalog(definitions)

    def loadCatalog(self, definitions):
        previous = self.list.blockSignals(True)
        try:
            self.list.clear()

            for definition in definitions:
                canonical = definition["canonical_name"]
                display = definition.get("display_name", canonical)
                category = definition.get("category", "")
                label = f"{category} · {display}" if category else display
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, canonical)
                item.setData(Qt.UserRole + 1, definition.get("catalog"))
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.list.addItem(item)
        finally:
            self.list.blockSignals(previous)
        self._apply_filters()

    # ------------------------------------------------

    def filter(self, text):
        self._apply_filters(text)

    def _apply_filters(self, text=None):
        if text is None:
            text = self.search.edit.text()
        text = str(text).lower()
        catalog = self.catalog.currentData()

        for i in range(self.list.count()):

            item = self.list.item(i)

            item.setHidden(
                text not in item.text().lower()
                or (catalog is not None and item.data(Qt.UserRole + 1) != catalog)
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
                    item.data(Qt.UserRole) or item.text()
                )

        return symbols

    # ------------------------------------------------

    def setSelected(self, symbols):
        symbols = set(symbols)
        previous = self.list.blockSignals(True)
        try:
            for i in range(self.list.count()):
                item = self.list.item(i)
                item.setCheckState(
                    Qt.Checked
                    if (item.data(Qt.UserRole) or item.text()) in symbols
                    else Qt.Unchecked
                )
        finally:
            self.list.blockSignals(previous)
