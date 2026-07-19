from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget, QFileDialog)

from services.live_readiness_certification import live_readiness_certification


class LiveReadinessPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.summary = QLabel()
        toolbar.addWidget(self.summary); toolbar.addStretch()
        refresh = QPushButton("Actualizar certificación"); refresh.clicked.connect(self.refresh); toolbar.addWidget(refresh)
        for report_type, label in (("json", "Exportar JSON"), ("html", "Exportar HTML"), ("txt", "Exportar TXT")):
            button = QPushButton(label); button.clicked.connect(lambda checked=False, kind=report_type: self.export(kind)); toolbar.addWidget(button)
        layout.addLayout(toolbar)
        self.table = QTableWidget(); self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Área", "Control", "Estado", "Detalle"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers); layout.addWidget(self.table)
        self.report = None; self.refresh()

    def refresh(self):
        self.report = live_readiness_certification.evaluate()
        self.summary.setText(f"Readiness: {self.report['score']}% | LIVE disponible: {'Sí' if self.report['available'] else 'No'} (órdenes bloqueadas)")
        self.table.setRowCount(len(self.report["items"]))
        for row, item in enumerate(self.report["items"]):
            for column, value in enumerate((item["section"], item["name"], item["status"], item["detail"])):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))

    def export(self, report_type):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar certificación", f"live_readiness.{report_type}")
        if path:
            live_readiness_certification.export(self.report, path, report_type)
