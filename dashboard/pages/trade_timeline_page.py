from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from repositories.execution_timeline_repository import execution_timeline_repository


class TradeTimelinePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        filters = QHBoxLayout()
        filters.addWidget(QLabel("Estado"))
        self.state = QComboBox()
        self.state.addItems(["Todos", "NEW", "PARSED", "VALIDATED", "RISK_APPROVED", "QUEUED", "SIMULATED", "EXECUTED", "TP1", "TP2", "TP3", "CLOSED", "REJECTED", "CANCELLED", "ERROR", "EXPIRED"])
        self.state.currentTextChanged.connect(self.refresh)
        filters.addWidget(self.state)
        self.summary = QLabel()
        filters.addWidget(self.summary)
        filters.addStretch()
        layout.addLayout(filters)
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Fecha", "Operación", "Anterior", "Estado", "Razón", "Perfil", "Símbolo", "Modo"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self):
        state = None if self.state.currentText() == "Todos" else self.state.currentText()
        events = execution_timeline_repository.get_all(state=state)
        self.table.setRowCount(len(events))
        for row, event in enumerate(events):
            values = [event["created_at"], event["operation_id"], event.get("previous_state", ""),
                      event.get("new_state", ""), event.get("description", ""), event.get("profile_id", ""),
                      event.get("symbol", ""), event.get("execution_mode", "")]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
        stats = execution_timeline_repository.statistics()
        self.summary.setText(f"Rechazo: {stats['rejection_rate']}% | Éxito simulado: {stats['simulation_success_rate']}%")
