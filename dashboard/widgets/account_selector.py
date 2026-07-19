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


class AccountSelector(QWidget):

    selectionChanged = Signal()

    addRequested = Signal()

    editRequested = Signal()

    deleteRequested = Signal()

    def __init__(self, parent=None):

        super().__init__(parent)

        layout = QVBoxLayout(self)

        self.search = SearchWidget()

        layout.addWidget(self.search)

        self.list = QListWidget()

        layout.addWidget(self.list)

        buttons = QHBoxLayout()

        self.btnAdd = QPushButton("Agregar")

        self.btnEdit = QPushButton("Editar")

        self.btnDelete = QPushButton("Eliminar")

        buttons.addWidget(self.btnAdd)

        buttons.addWidget(self.btnEdit)

        buttons.addWidget(self.btnDelete)

        layout.addLayout(buttons)

        self.search.searchChanged.connect(
            self.filter
        )

        self.btnAdd.clicked.connect(
            self.addRequested.emit
        )

        self.btnEdit.clicked.connect(
            self.editRequested.emit
        )

        self.btnDelete.clicked.connect(
            self.deleteRequested.emit
        )

        self.list.itemChanged.connect(
            self.selectionChanged.emit
        )

    # ------------------------------------------------

    def loadAccounts(self, accounts):

        self.list.clear()

        for account in accounts:

            if hasattr(account, "name"):

                text = account.name

            elif isinstance(account, dict):

                text = account.get(
                    "name",
                    str(account),
                )

            else:

                text = str(account)

            item = QListWidgetItem(text)

            item.setData(
                Qt.UserRole,
                account,
            )

            item.setFlags(
                item.flags() |
                Qt.ItemIsUserCheckable
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

    def selectedAccounts(self):

        result = []

        for i in range(self.list.count()):

            item = self.list.item(i)

            if item.checkState() == Qt.Checked:

                result.append(
                    item.data(
                        Qt.UserRole
                    )
                )

        return result

    # ------------------------------------------------

    def currentAccount(self):

        item = self.list.currentItem()

        if item is None:

            return None

        return item.data(
            Qt.UserRole
        )

    # ------------------------------------------------

    def setSelected(self, ids):

        ids = set(ids)

        for i in range(self.list.count()):

            item = self.list.item(i)

            obj = item.data(
                Qt.UserRole
            )

            account_id = getattr(
                obj,
                "id",
                None,
            )

            item.setCheckState(

                Qt.Checked
                if account_id in ids
                else Qt.Unchecked

            )