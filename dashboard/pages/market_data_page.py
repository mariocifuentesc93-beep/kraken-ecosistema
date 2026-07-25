from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from config.symbols import BRIDGE_CATALOG, get_symbols
from services.market_data_service import market_data_service


class MarketDataPage(QWidget):
    """Read-only visibility into prices used by simulation."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Datos de mercado (solo lectura)"))
        toolbar.addStretch()
        refresh = QPushButton("Actualizar")
        refresh.clicked.connect(self.refresh)
        toolbar.addWidget(refresh)
        layout.addLayout(toolbar)
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(["Símbolo", "Bid", "Ask", "Último", "Spread", "Actualizado", "Fuente", "Disponible", "Estado"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self):
        symbols = get_symbols(BRIDGE_CATALOG)
        self.table.setRowCount(len(symbols))
        for row, symbol in enumerate(symbols):
            quote = market_data_service.quote(symbol)
            timestamp = quote["timestamp"]
            values = [symbol, quote["bid"], quote["ask"], quote["last"], quote["spread"], timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "", quote["source"], "Sí" if quote["available"] else "No", "Fresco" if quote["fresh"] else "Vencido"]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem("" if value is None else str(value)))
