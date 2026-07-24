from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)

from repositories.log_repository import log_repository


class LogsPage(QWidget):

    def __init__(self):

        super().__init__()

        self.build_ui()

        self.timer = QTimer()

        self.timer.timeout.connect(self.refresh)

        self.timer.start(3000)

        self.refresh()

    # ======================================================

    def build_ui(self):

        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()

        layout.addLayout(toolbar)

        toolbar.addWidget(QLabel("Nivel"))

        self.cbo_level = QComboBox()

        self.cbo_level.addItems([
            "Todos",
            "INFO",
            "WARNING",
            "ERROR",
            "DEBUG",
        ])

        self.cbo_level.currentIndexChanged.connect(
            self.refresh
        )

        toolbar.addWidget(self.cbo_level)

        toolbar.addWidget(QLabel("Buscar"))

        self.txt_search = QLineEdit()
        self.txt_search.setObjectName("EnterpriseSearch")
        self.txt_search.setPlaceholderText("Buscar registros")

        self.txt_search.textChanged.connect(
            self.refresh
        )

        toolbar.addWidget(self.txt_search)

        self.btn_clear = QPushButton(
            "Limpiar"
        )

        self.btn_refresh = QPushButton(
            "Actualizar"
        )

        toolbar.addWidget(self.btn_clear)

        toolbar.addStretch()

        toolbar.addWidget(self.btn_refresh)

        self.table = QTableWidget()

        layout.addWidget(self.table)

        self.table.setColumnCount(5)

        self.table.setHorizontalHeaderLabels([

            "Fecha",
            "Nivel",
            "Módulo",
            "Mensaje",
            "ID",

        ])

        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        self.table.setSelectionBehavior(
            QTableWidget.SelectRows
        )

        self.table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        self.table.setAlternatingRowColors(
            True
        )

        self.btn_refresh.clicked.connect(
            self.refresh
        )

        self.btn_clear.clicked.connect(
            self.clear_logs
        )

    # ======================================================

    def refresh(self):

        level = self.cbo_level.currentText()

        search = self.txt_search.text().lower()

        logs = log_repository.get_all()

        rows = []

        for log in logs:

            if level != "Todos":

                if log["level"] != level:

                    continue

            if search:

                text = (
                    f"{log['module']} "
                    f"{log['message']}"
                ).lower()

                if search not in text:

                    continue

            rows.append(log)

        self.table.setRowCount(len(rows))

        for row, log in enumerate(rows):

            values = [

                log["created_at"],

                log["level"],

                log["module"],

                log["message"],

                log["id"],

            ]

            for column, value in enumerate(values):

                item = QTableWidgetItem(
                    str(value)
                )

                item.setTextAlignment(
                    Qt.AlignCenter
                )

                self.table.setItem(
                    row,
                    column,
                    item,
                )

    # ======================================================

    def clear_logs(self):

        log_repository.clear()

        self.refresh()
