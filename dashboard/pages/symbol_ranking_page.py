from datetime import date

from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from services.symbol_ranking_service import symbol_ranking_service
from services.trading_calendar_service import trading_calendar_service


class SymbolRankingPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self.refresh()

    def _build(self):
        layout = QVBoxLayout(self)
        filters = QHBoxLayout()
        self.start = QDateEdit()
        self.end = QDateEdit()
        self.start.setCalendarPopup(True)
        self.end.setCalendarPopup(True)
        self.start.setDate(date(date.today().year, 1, 1))
        self.end.setDate(date.today())
        self.profile = QComboBox()
        self.account = QComboBox()
        self.mode = QComboBox()
        self.source = QComboBox()
        self.direction = QComboBox()
        for label, widget in (
            ("Desde", self.start), ("Hasta", self.end),
            ("Perfil", self.profile), ("Cuenta", self.account),
            ("Modo", self.mode), ("Fuente", self.source),
            ("Dirección", self.direction),
        ):
            filters.addWidget(QLabel(label))
            filters.addWidget(widget)
        button = QPushButton("Actualizar")
        button.clicked.connect(self.refresh)
        filters.addWidget(button)
        layout.addLayout(filters)

        self.summary = QLabel(
            "El ranking pondera TP1, TP2 y TP3 alcanzados y penaliza Stop Loss."
        )
        layout.addWidget(self.summary)
        self.table = QTableWidget()
        headers = [
            "#", "Símbolo", "Operaciones", "TP1", "% TP1", "TP2", "% TP2",
            "TP3", "% TP3", "SL", "% SL", "Wins", "Win rate", "P/L", "Score",
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

    @staticmethod
    def _fill(combo, items):
        selected = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Todos", None)
        for label, value in items:
            combo.addItem(str(label), value)
        index = combo.findData(selected)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    def filters(self):
        return {
            "start": self.start.date().toPython(),
            "end": self.end.date().toPython(),
            "profile": self.profile.currentData(),
            "account": self.account.currentData(),
            "mode": self.mode.currentData(),
            "source": self.source.currentData(),
            "direction": self.direction.currentData(),
        }

    def refresh(self):
        options = trading_calendar_service.filter_options()
        self._fill(
            self.profile,
            [(name, identifier) for identifier, name in options["profiles"]],
        )
        self._fill(
            self.account,
            [(name, identifier) for identifier, name in options["accounts"]],
        )
        for combo, key in (
            (self.mode, "modes"), (self.source, "sources"),
            (self.direction, "directions"),
        ):
            self._fill(combo, [(value, value) for value in options[key]])

        rows = symbol_ranking_service.ranking(self.filters())
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = (
                row["rank"], row["symbol"], row["operations"],
                row["tp1"], row["tp1_rate"], row["tp2"], row["tp2_rate"],
                row["tp3"], row["tp3_rate"], row["sl"], row["sl_rate"],
                row["wins"], row["win_rate"], round(row["net"], 2),
                row["score"],
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem()
                item.setData(0, value)
                self.table.setItem(row_index, column, item)
        self.table.setSortingEnabled(True)
        self.summary.setText(
            f"Símbolos clasificados: {len(rows)}. "
            "Score = %TP1 + 2×%TP2 + 3×%TP3 − %SL."
        )
