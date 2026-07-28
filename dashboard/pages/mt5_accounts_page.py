from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QFileDialog,
    QLabel,
)

from repositories.mt5_account_repository import mt5_account_repository
from repositories.mt5_terminal_repository import mt5_terminal_repository
from services.mt5_connection_registry import mt5_connection_registry
from services.mt5_connection_diagnostics import mt5_connection_diagnostics
from models.mt5_account import MT5Account
from dashboard.dialogs.mt5_account_dialog import MT5AccountDialog
from dashboard.ui_theme import set_visual_role


class MT5AccountsPage(QWidget):

    def __init__(self):

        super().__init__()

        self.build_ui()

        self.refresh()

    # ======================================================

    def build_ui(self):

        layout = QVBoxLayout(self)
        layout.setSpacing(9)

        toolbar = QGridLayout()

        layout.addLayout(toolbar)

        self.btn_new = QPushButton("Nueva")

        self.btn_edit = QPushButton("Editar")

        self.btn_delete = QPushButton("Eliminar")

        self.btn_test = QPushButton("Probar conexión")

        self.btn_export_json = QPushButton("Exportar JSON")

        self.btn_export_text = QPushButton("Exportar TXT")

        self.btn_refresh = QPushButton("Actualizar")

        for index, button in enumerate((self.btn_new, self.btn_edit, self.btn_delete,
                                        self.btn_test, self.btn_export_json,
                                        self.btn_export_text, self.btn_refresh)):
            toolbar.addWidget(button, index // 4, index % 4)
        for column in range(4):
            toolbar.setColumnStretch(column, 1)

        self.summary = QLabel("Sin cuentas MT5 configuradas. Agregue una cuenta para consultar su estado y diagnóstico.")
        self.summary.setWordWrap(True)
        set_visual_role(self.summary, "information")
        layout.addWidget(self.summary)

        self.table = QTableWidget()

        layout.addWidget(self.table)

        self.table.setColumnCount(13)

        self.table.setHorizontalHeaderLabels([

            "ID",
            "Nombre",
            "Broker",
            "Login",
            "Servidor",
            "Estado",
            "Balance",
            "Equity",
            "Magic",
            "Comentario",
            "Desviación",
            "Lote",
            "Activo",

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

        self.table.setAlternatingRowColors(True)

        self.btn_refresh.clicked.connect(
            self.refresh
        )

        self.btn_new.clicked.connect(self.new_account)

        self.btn_edit.clicked.connect(self.edit_account)

        self.btn_delete.clicked.connect(self.delete_account)

        self.btn_test.clicked.connect(
            self.test_connection
        )

        self.btn_export_json.clicked.connect(lambda: self.export_diagnostic("json"))
        self.btn_export_text.clicked.connect(lambda: self.export_diagnostic("text"))
        self.last_diagnostic = None

    # ======================================================

    def refresh(self):

        accounts = mt5_account_repository.get_all()

        worker_status = mt5_connection_registry.status()
        connected = sum(
            1
            for account in accounts
            if getattr(account, "mt5_terminal_id", None)
            and worker_status.get(
                (int(account.mt5_terminal_id), int(account.id)), {}
            ).get("alive", False)
        )
        self.summary.setText(
            f"Cuentas configuradas: {len(accounts)} · Conectadas: {connected} · "
            "Seleccione una cuenta y use Probar conexión para ver el diagnóstico."
        )

        self.table.setRowCount(len(accounts))

        for row, account in enumerate(accounts):

            values = [

                account.id,
                account.name,
                account.server,
                account.login,
                account.server,
                "🟢" if (
                    getattr(account, "mt5_terminal_id", None)
                    and worker_status.get(
                        (
                            int(account.mt5_terminal_id),
                            int(account.id),
                        ),
                        {},
                    ).get("alive", False)
                ) else "🔴",
                f"{getattr(account,'balance',0):,.2f}",
                f"{getattr(account,'equity',0):,.2f}",
                account.magic_number,
                account.comment,
                account.deviation,
                account.fixed_lot,
                "Sí" if account.enabled else "No",

            ]

            for column, value in enumerate(values):

                item = QTableWidgetItem(str(value))

                item.setTextAlignment(Qt.AlignCenter)

                self.table.setItem(
                    row,
                    column,
                    item,
                )

    # ======================================================

    def selected_account(self):

        row = self.table.currentRow()

        if row < 0:

            return None

        account_id = int(
            self.table.item(row, 0).text()
        )

        return mt5_account_repository.get_by_id(
            account_id
        )

    def _apply_dialog_data(self, account, data):
        account.name = data["name"]
        account.login = int(data["login"])
        account.password = data["password"]
        account.server = data["server"]
        account.terminal_path = data["terminal_path"]
        account.mt5_terminal_id = data.get("mt5_terminal_id")
        account.active = data["enabled"]
        account.auto_connect = data["auto_reconnect"]
        account.execution_mode = data["environment"]
        account.deviation = data["deviation"]
        return account

    def new_account(self):
        dialog = MT5AccountDialog(parent=self)
        if dialog.exec():
            try:
                mt5_account_repository.create(
                    self._apply_dialog_data(MT5Account(), dialog.get_account_data())
                )
                self.refresh()
            except (TypeError, ValueError) as error:
                QMessageBox.critical(self, "MT5", f"No se pudo guardar la cuenta: {error}")

    def edit_account(self):
        account = self.selected_account()
        if account is None:
            QMessageBox.warning(self, "MT5", "Seleccione una cuenta.")
            return
        dialog = MT5AccountDialog(account=account, parent=self)
        if dialog.exec():
            try:
                mt5_account_repository.update(
                    self._apply_dialog_data(account, dialog.get_account_data())
                )
                self.refresh()
            except (TypeError, ValueError) as error:
                QMessageBox.critical(self, "MT5", f"No se pudo actualizar la cuenta: {error}")

    def delete_account(self):
        account = self.selected_account()
        if account is None:
            QMessageBox.warning(self, "MT5", "Seleccione una cuenta.")
            return
        if QMessageBox.question(
            self,
            "Eliminar cuenta MT5",
            f"¿Desea eliminar '{account.name}'?",
            QMessageBox.Yes | QMessageBox.No,
        ) == QMessageBox.Yes:
            mt5_account_repository.delete(account.id)
            self.refresh()

    # ======================================================

    def test_connection(self):

        account = self.selected_account()

        if account is None:

            QMessageBox.warning(
                self,
                "MT5",
                "Seleccione una cuenta."
            )

            return

        try:
            connection = mt5_connection_registry.connection_for(
                account.id,
                account.mt5_terminal_id,
            )
            terminal = mt5_terminal_repository.get_by_id(
                account.mt5_terminal_id
            )
            self.last_diagnostic = (
                mt5_connection_diagnostics.run_connected(
                    account,
                    connection,
                    catalog_id=getattr(
                        terminal,
                        "catalog_id",
                        "BRIDGE_SYNTHETICS",
                    ),
                )
            )
        except Exception as error:
            QMessageBox.critical(
                self,
                "Diagnóstico MT5",
                f"No se pudo conectar la cuenta aislada: {error}",
            )
            self.refresh()
            return
        report = self.last_diagnostic
        validated = sum(row["tick_available"] for row in report["symbols"])
        message = (
            f"Terminal: {report['terminal_path']}\nCuenta: {report['account']}\n"
            f"Servidor: {report['server']}\nBalance: {report['balance']}\n"
            f"Equity: {report['equity']}\nMoneda: {report['currency']}\n"
            f"Apalancamiento: {report['leverage']}\nTrading permitido: {report['trade_allowed']}\n"
            f"Algoritmos permitidos: {report['algorithmic_trading_allowed']}\n"
            f"Conectado: {report['connected_timestamp']}\n"
            f"Símbolos validados: {validated}/{len(report['symbols'])}\n\n"
            f"{report['actionable_error'] or report['last_error']}"
        )
        if report["success"]:
            account.balance = report["balance"] or 0.0
            account.equity = report["equity"] or 0.0
            QMessageBox.information(self, "Diagnóstico MT5", message)
        else:
            QMessageBox.critical(self, "Diagnóstico MT5", message)
        self.refresh()

    def export_diagnostic(self, report_type):
        if not self.last_diagnostic:
            QMessageBox.warning(self, "MT5", "Primero ejecute 'Probar conexión'.")
            return
        suffix = "json" if report_type == "json" else "txt"
        path, _ = QFileDialog.getSaveFileName(self, "Exportar diagnóstico", f"mt5_diagnostic.{suffix}")
        if not path:
            return
        if report_type == "json":
            mt5_connection_diagnostics.export_json(self.last_diagnostic, path)
        else:
            mt5_connection_diagnostics.export_text(self.last_diagnostic, path)
        QMessageBox.information(self, "MT5", "Diagnóstico exportado correctamente.")
