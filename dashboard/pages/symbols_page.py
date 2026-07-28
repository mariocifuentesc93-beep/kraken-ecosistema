from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config.symbols import get_symbol_catalog
from repositories.profile_repository import profile_repository
from repositories.symbol_repository import symbol_repository


CATALOG_LABELS = {
    "BRIDGE_SYNTHETICS": "Bridge Markets",
    "WELTRADE_SYNTHETICS": "Weltrade",
}


class SymbolsPage(QWidget):
    """Profile selection over the fixed Bridge and Weltrade catalogs."""

    def __init__(self):
        super().__init__()
        self._rows = []
        self.build_ui()
        self.load_profiles()
        self.refresh()

    def build_ui(self):
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        layout.addLayout(toolbar)

        toolbar.addWidget(QLabel("Perfil"))
        self.cbo_profile = QComboBox()
        self.cbo_profile.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.cbo_profile)

        toolbar.addWidget(QLabel("Catálogo"))
        self.cbo_catalog = QComboBox()
        self.cbo_catalog.addItem("Todos", None)
        self.cbo_catalog.addItem("Bridge Markets", "BRIDGE_SYNTHETICS")
        self.cbo_catalog.addItem("Weltrade", "WELTRADE_SYNTHETICS")
        self.cbo_catalog.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.cbo_catalog)

        self.btn_enable = QPushButton("Activar")
        self.btn_disable = QPushButton("Desactivar")
        self.btn_enable_all = QPushButton("Activar visibles")
        self.btn_disable_all = QPushButton("Desactivar visibles")
        self.btn_refresh = QPushButton("Actualizar")
        for button in (
            self.btn_enable,
            self.btn_disable,
            self.btn_enable_all,
            self.btn_disable_all,
        ):
            toolbar.addWidget(button)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(
            [
                "ID selección",
                "Símbolo",
                "Nombre",
                "Catálogo",
                "Broker",
                "Categoría",
                "Activo",
                "Disponibilidad",
                "Símbolo MT5",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_enable.clicked.connect(lambda: self._set_selected(True))
        self.btn_disable.clicked.connect(lambda: self._set_selected(False))
        self.btn_enable_all.clicked.connect(lambda: self._set_all_visible(True))
        self.btn_disable_all.clicked.connect(lambda: self._set_all_visible(False))

    def load_profiles(self):
        current = self.cbo_profile.currentData()
        self.cbo_profile.blockSignals(True)
        self.cbo_profile.clear()
        for profile in profile_repository.get_all():
            self.cbo_profile.addItem(profile.name, profile.id)
        index = self.cbo_profile.findData(current)
        if index >= 0:
            self.cbo_profile.setCurrentIndex(index)
        self.cbo_profile.blockSignals(False)

    def _visible_catalog(self):
        return get_symbol_catalog(self.cbo_catalog.currentData())

    def refresh(self, *_):
        if self.cbo_profile.count() == 0:
            self.table.setRowCount(0)
            return
        profile_id = self.cbo_profile.currentData()
        selected = {
            symbol.symbol: symbol
            for symbol in symbol_repository.get_all(profile_id)
        }
        self._rows = self._visible_catalog()
        known = {item["canonical_name"] for item in self._rows}
        if self.cbo_catalog.currentData() is None:
            self._rows.extend(
                {
                    "canonical_name": name,
                    "display_name": name,
                    "mt5_symbol": record.mt5_symbol,
                    "catalog": "LEGACY",
                    "broker": "—",
                    "category": "LEGACY",
                    "enabled": record.enabled,
                    "sort_order": 0,
                }
                for name, record in selected.items()
                if name not in known
            )
        self.table.setRowCount(len(self._rows))
        for row, definition in enumerate(self._rows):
            record = selected.get(definition["canonical_name"])
            values = (
                record.id if record else "—",
                definition["canonical_name"],
                definition["display_name"],
                CATALOG_LABELS.get(definition["catalog"], definition["catalog"]),
                definition["broker"],
                definition["category"],
                "Sí" if record and record.enabled else "No",
                "NO VERIFICADO",
                definition["mt5_symbol"],
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                item.setData(Qt.UserRole, definition["canonical_name"])
                self.table.setItem(row, column, item)

    def _selected_definition(self):
        row = self.table.currentRow()
        return self._rows[row] if 0 <= row < len(self._rows) else None

    def _set_selected(self, enabled):
        definition = self._selected_definition()
        if definition is None:
            return
        self._upsert_selection(definition, enabled)
        self.refresh()

    def enable_symbol(self):
        self._set_selected(True)

    def disable_symbol(self):
        self._set_selected(False)

    def enable_all(self):
        self._set_all_visible(True)

    def disable_all(self):
        self._set_all_visible(False)

    def _set_all_visible(self, enabled):
        for definition in self._rows:
            self._upsert_selection(definition, enabled)
        QMessageBox.information(
            self,
            "Símbolos",
            "Los símbolos visibles fueron actualizados.",
        )
        self.refresh()

    def _upsert_selection(self, definition, enabled):
        profile_id = self.cbo_profile.currentData()
        record = symbol_repository.get_by_symbol(
            profile_id, definition["canonical_name"]
        )
        if record is None:
            symbol_repository.create(
                profile_id,
                enabled,
                definition["canonical_name"],
                definition["mt5_symbol"],
                definition["display_name"],
                "",
                1.0,
                0.01,
                100.0,
                "trade",
                definition["catalog"],
            )
            return
        symbol_repository.update(
            record.id,
            enabled,
            definition["mt5_symbol"],
            definition["display_name"],
            record.aliases,
            record.risk,
            record.min_lot,
            record.max_lot,
            record.action,
        )
