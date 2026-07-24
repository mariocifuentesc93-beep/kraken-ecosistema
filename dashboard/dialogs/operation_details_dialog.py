from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QPushButton,
    QLabel,
    QFormLayout,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
)

from dashboard.widgets.section_widget import SectionWidget
from dashboard.widgets.statistics_panel import StatisticsPanel
from dashboard.dialogs.dialog_layout import fit_dialog_to_screen


class OperationDetailsDialog(QDialog):

    def __init__(self, operation=None, parent=None):

        super().__init__(parent)

        self.operation = operation

        self.setWindowTitle("Detalle de Operación")

        fit_dialog_to_screen(self, 1200, 700)

        self.build_ui()

    # --------------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()

        layout.addWidget(self.tabs)

        self.build_summary_tab()

        self.build_signal_tab()

        self.build_execution_tab()

        self.build_events_tab()

        self.build_logs_tab()

        self.build_statistics_tab()

        buttons = QHBoxLayout()

        buttons.addStretch()

        self.btnClose = QPushButton("Cerrar")

        buttons.addWidget(self.btnClose)

        layout.addLayout(buttons)

        self.btnClose.clicked.connect(self.accept)

    def build_summary_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget(
            "Resumen"
        )

        form = QFormLayout()

        self.lblTicket = QLabel("-")

        self.lblSymbol = QLabel("-")

        self.lblDirection = QLabel("-")

        self.lblVolume = QLabel("-")

        self.lblEntry = QLabel("-")

        self.lblSL = QLabel("-")

        self.lblTP = QLabel("-")

        self.lblStatus = QLabel("-")

        self.lblProfit = QLabel("-")

        form.addRow("Ticket", self.lblTicket)

        form.addRow("Símbolo", self.lblSymbol)

        form.addRow("Dirección", self.lblDirection)

        form.addRow("Volumen", self.lblVolume)

        form.addRow("Entrada", self.lblEntry)

        form.addRow("SL", self.lblSL)

        form.addRow("TP", self.lblTP)

        form.addRow("Estado", self.lblStatus)

        form.addRow("Resultado", self.lblProfit)

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(page, "Resumen")

    def build_signal_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget(
            "Señal Telegram"
        )

        self.signalText = QPlainTextEdit()

        self.signalText.setReadOnly(True)

        section.addWidget(self.signalText)

        layout.addWidget(section)

        self.tabs.addTab(page, "Señal")

    def build_execution_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        self.executionTable = QTableWidget()

        self.executionTable.setColumnCount(8)

        self.executionTable.setHorizontalHeaderLabels([

            "Cuenta",

            "Ticket",

            "Estado",

            "Entrada",

            "SL",

            "TP",

            "Resultado",

            "Hora"

        ])

        layout.addWidget(self.executionTable)

        self.tabs.addTab(page, "Ejecución")

    def build_events_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        self.eventsTable = QTableWidget()

        self.eventsTable.setColumnCount(3)

        self.eventsTable.setHorizontalHeaderLabels([

            "Hora",

            "Evento",

            "Descripción"

        ])

        layout.addWidget(self.eventsTable)

        self.tabs.addTab(page, "Eventos")

    def build_logs_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        self.logs = QPlainTextEdit()

        self.logs.setReadOnly(True)

        layout.addWidget(self.logs)

        self.tabs.addTab(page, "Logs")

    def build_statistics_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        self.statistics = StatisticsPanel()

        layout.addWidget(self.statistics)

        layout.addStretch()

        self.tabs.addTab(page, "Estadísticas")

    def load_operation(self, operation):

        if operation is None:

            return

        self.operation = operation

        self.lblTicket.setText(
            str(getattr(operation, "ticket", "-"))
        )

        self.lblSymbol.setText(
            getattr(operation, "symbol", "-")
        )

        self.lblDirection.setText(
            getattr(operation, "direction", "-")
        )

        self.lblVolume.setText(
            str(getattr(operation, "volume", "-"))
        )

        self.lblEntry.setText(
            str(getattr(operation, "entry", "-"))
        )

        self.lblSL.setText(
            str(getattr(operation, "sl", "-"))
        )

        self.lblTP.setText(
            str(getattr(operation, "tp", "-"))
        )

        self.lblStatus.setText(
            getattr(operation, "status", "-")
        )

        self.lblProfit.setText(
            str(getattr(operation, "profit", 0))
        )

        self.signalText.setPlainText(
            getattr(operation, "telegram_message", "")
        )

    def set_execution_history(self, executions):

        self.executionTable.setRowCount(0)

        for execution in executions:

            row = self.executionTable.rowCount()

            self.executionTable.insertRow(row)

            values = [

                execution.get("account"),

                execution.get("ticket"),

                execution.get("status"),

                execution.get("entry"),

                execution.get("sl"),

                execution.get("tp"),

                execution.get("profit"),

                execution.get("time")

            ]

            for col, value in enumerate(values):

                self.executionTable.setItem(

                    row,

                    col,

                    QTableWidgetItem(str(value))

                )

    def set_events(self, events):

        self.eventsTable.setRowCount(0)

        for event in events:

            row = self.eventsTable.rowCount()

            self.eventsTable.insertRow(row)

            values = [

                event.get("time"),

                event.get("event"),

                event.get("description")

            ]

            for col, value in enumerate(values):

                self.eventsTable.setItem(

                    row,

                    col,

                    QTableWidgetItem(str(value))

                )

    def set_logs(self, logs):

        self.logs.setPlainText(

            "\n".join(logs)

        )

    def set_statistics(self, statistics):

        if not statistics:

            self.statistics.clear()

            return

        for key, value in statistics.items():

            self.statistics.setValue(

                key,

                value

            )

