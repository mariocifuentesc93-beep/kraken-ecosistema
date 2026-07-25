from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from models.mt5_terminal import MT5Terminal
from repositories.mt5_terminal_repository import mt5_terminal_repository
from services.mt5_terminal_launcher import MT5TerminalLauncher


class MT5TerminalsPage(QWidget):
    HEADERS = ("ID", "Nombre", "Rol", "Broker", "Catálogo", "Ejecutable",
               "Carpeta de datos", "Estado")

    def __init__(self, repository=None, launcher=None, parent=None):
        super().__init__(parent)
        self.repository = repository or mt5_terminal_repository
        self.launcher = launcher or MT5TerminalLauncher()
        layout = QVBoxLayout(self)
        self.notice = QLabel("Inventario multi-terminal; no modifica instalaciones.")
        layout.addWidget(self.notice)
        actions = QHBoxLayout()
        self.add_button = QPushButton("Registrar instalación")
        self.refresh_button = QPushButton("Actualizar")
        self.launch_button = QPushButton("Iniciar terminal")
        for button in (self.add_button, self.refresh_button, self.launch_button):
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)
        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)
        self.refresh_button.clicked.connect(self.refresh)
        self.add_button.clicked.connect(self.register_installation)
        self.launch_button.clicked.connect(self.launch_selected)
        self.refresh()

    def refresh(self):
        terminals = self.repository.get_all()
        self.table.setRowCount(len(terminals))
        for row, terminal in enumerate(terminals):
            values = (terminal.id, terminal.name, terminal.role, terminal.broker,
                      terminal.catalog_id, terminal.executable_path,
                      terminal.data_path, terminal.connection_status)
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value or ""))
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.table.setItem(row, column, item)
        if not getattr(self.repository, "_available", lambda: True)():
            self.notice.setText(
                "Migración pendiente: ejecútela explícitamente tras un respaldo."
            )

    def selected_terminal(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        return self.repository.get_by_id(int(self.table.item(row, 0).text()))

    def register_installation(self):
        executable, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar terminal MT5", "", "MetaTrader (terminal64.exe)"
        )
        if not executable:
            return
        data_path = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta de datos"
        )
        try:
            self.repository.save(MT5Terminal(
                name=f"MT5 {self.table.rowCount() + 1}",
                executable_path=executable, data_path=data_path,
            ))
            self.refresh()
        except Exception as error:
            QMessageBox.critical(self, "Terminales MT5", str(error))

    def launch_selected(self):
        terminal = self.selected_terminal()
        if terminal is None:
            QMessageBox.warning(self, "Terminales MT5", "Seleccione un terminal.")
            return
        future = self.launcher.launch_async(terminal)
        def record(result):
            error = result.exception()
            self.repository.set_runtime_status(
                terminal.id, "ERROR" if error else "RUNNING",
                None if error else result.result(),
            )
        future.add_done_callback(record)
