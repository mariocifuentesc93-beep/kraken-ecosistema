import json

from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from repositories.signal_repository import signal_repository


class SignalInspectorPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Estado"))
        self.filter = QComboBox()
        self.filter.addItems([
            "Todos",
            "RECEIVED",
            "ROUTED",
            "ACCEPTED",
            "REJECTED",
            "FAILED",
            "EXECUTED",
            "SIMULATED",
        ])
        self.filter.currentTextChanged.connect(self.refresh)
        toolbar.addWidget(self.filter)
        self.refresh_button = QPushButton("Actualizar")
        self.refresh_button.clicked.connect(self.refresh)
        toolbar.addWidget(self.refresh_button)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Origen", "Perfil", "Símbolo", "Estado", "Score", "Decisión"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.show_selected)
        layout.addWidget(self.table)

        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        layout.addWidget(self.details)
        self.signals = []
        self.refresh()

    def refresh(self):
        status = self.filter.currentText()
        self.signals = [signal for signal in signal_repository.get_all()
                        if status == "Todos" or signal.status == status]
        self.table.setRowCount(len(self.signals))
        for row, signal in enumerate(self.signals):
            routed_profiles = signal.metadata.get("routed_profiles", [])
            profile = ", ".join(
                item.get("name", str(item.get("id", "")))
                for item in routed_profiles
            ) or signal.profile_name or signal.profile_id or ""
            values = [signal.id, signal.source, profile, signal.symbol,
                      signal.status, f"{signal.score:.0f}", signal.execution_decision]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))

    def show_selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.signals):
            return
        signal = self.signals[row]
        payload = {
            "raw_message": signal.raw_message,
            "parsed_fields": signal.metadata.get("parsed_fields", {}),
            "validation_status": signal.status,
            "profile": signal.profile_name or signal.profile_id,
            "routed_profiles": signal.metadata.get("routed_profiles", []),
            "routing_attempts": signal.metadata.get("routing_attempts", []),
            "failure_stage": signal.metadata.get("failure_stage", ""),
            "rejection_reason": signal.rejection_reason,
            "traceback": signal.metadata.get("traceback", ""),
            "trade_request": signal.metadata.get("trade_request", {}),
            "final_execution_decision": signal.execution_decision,
        }
        self.details.setPlainText(json.dumps(payload, ensure_ascii=False, indent=2))
