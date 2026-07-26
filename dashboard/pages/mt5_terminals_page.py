import os
from pathlib import Path

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dashboard.dialogs.mt5_terminal_dialog import (
    MT5AccountSyncDialog,
    MT5TerminalDialog,
)
from models.mt5_terminal import MT5Terminal
from repositories.mt5_account_repository import mt5_account_repository
from repositories.mt5_terminal_repository import mt5_terminal_repository
from services.mt5_installation_discovery_service import (
    MT5InstallationDiscoveryService,
)
from services.mt5_terminal_launcher import MT5TerminalLauncher
from services.mt5_terminal_lifecycle_service import (
    MT5TerminalLifecycleError,
    mt5_terminal_lifecycle_service,
)


class MT5TerminalsPage(QWidget):
    launchFinished = Signal(object, object)

    HEADERS = (
        "ID",
        "Nombre",
        "Ejecutable",
        "Data folder",
        "Broker",
        "Catálogo",
        "Trading",
        "Scanner",
        "Activa",
        "Proceso",
        "Cuenta esperada",
        "Cuenta detectada",
        "Coincidencia",
        "Estado",
    )

    def __init__(
        self,
        repository=None,
        launcher=None,
        account_repository=None,
        lifecycle_service=None,
        discovery_service=None,
        parent=None,
    ):
        super().__init__(parent)
        self.repository = repository or mt5_terminal_repository
        self.launcher = launcher or MT5TerminalLauncher()
        self.account_repository = (
            account_repository or mt5_account_repository
        )
        self.lifecycle = (
            lifecycle_service or mt5_terminal_lifecycle_service
        )
        self.discovery = (
            discovery_service or MT5InstallationDiscoveryService()
        )
        self._discoveries = []
        self._build_ui()
        self._connect_events()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.notice = QLabel(
            "Inventario administrado de instalaciones MT5. "
            "Kraken nunca elimina archivos físicos."
        )
        self.notice.setWordWrap(True)
        layout.addWidget(self.notice)

        first_row = QHBoxLayout()
        second_row = QHBoxLayout()
        layout.addLayout(first_row)
        layout.addLayout(second_row)

        self.detect_button = QPushButton("Detectar instalaciones")
        self.register_button = QPushButton("Registrar")
        self.edit_button = QPushButton("Editar")
        self.state_sync_button = QPushButton("Sincronizar")
        self.sync_button = QPushButton("Sincronizar cuenta")
        self.toggle_button = QPushButton("Habilitar / Deshabilitar")
        self.launch_button = QPushButton("Abrir terminal")
        self.change_paths_button = QPushButton("Cambiar rutas")
        self.open_data_button = QPushButton("Abrir carpeta de datos")
        self.diagnose_button = QPushButton("Diagnosticar")
        self.delete_button = QPushButton("Eliminar")
        self.refresh_button = QPushButton("Actualizar")
        self.add_button = self.register_button  # legacy UI/test alias

        for button in (
            self.detect_button,
            self.register_button,
            self.edit_button,
            self.state_sync_button,
            self.sync_button,
            self.toggle_button,
        ):
            first_row.addWidget(button)
        first_row.addStretch()
        for button in (
            self.launch_button,
            self.change_paths_button,
            self.open_data_button,
            self.diagnose_button,
            self.delete_button,
            self.refresh_button,
        ):
            second_row.addWidget(button)
        second_row.addStretch()

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

    def _connect_events(self):
        self.refresh_button.clicked.connect(self.refresh)
        self.detect_button.clicked.connect(self.detect_installations)
        self.register_button.clicked.connect(self.register_installation)
        self.edit_button.clicked.connect(self.edit_selected)
        self.state_sync_button.clicked.connect(self.synchronize_state)
        self.sync_button.clicked.connect(self.synchronize_selected)
        self.toggle_button.clicked.connect(self.toggle_selected)
        self.launch_button.clicked.connect(self.launch_selected)
        self.change_paths_button.clicked.connect(self.change_selected_paths)
        self.open_data_button.clicked.connect(self.open_data_folder)
        self.diagnose_button.clicked.connect(self.diagnose_selected)
        self.delete_button.clicked.connect(self.delete_selected)
        self.table.itemSelectionChanged.connect(self._update_actions)
        self.launchFinished.connect(self._finish_launch)

    def refresh(self, *_args):
        selected_id = getattr(self.selected_terminal(), "id", None)
        terminals = self.repository.get_all()
        expected_accounts = {}
        try:
            for account in self.account_repository.get_all():
                terminal_id = getattr(account, "mt5_terminal_id", None)
                if terminal_id is not None:
                    expected_accounts.setdefault(terminal_id, []).append(
                        f"{account.login} · {account.server}"
                    )
        except Exception:
            expected_accounts = {}
        sorting_enabled = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        try:
            self.table.setRowCount(len(terminals))
            selected_row = -1
            for row, terminal in enumerate(terminals):
                expected = " / ".join(
                    expected_accounts.get(terminal.id, ())
                ) or "—"
                detected = " · ".join(
                    str(value)
                    for value in (
                        terminal.detected_login,
                        terminal.detected_server,
                    )
                    if value not in (None, "")
                ) or "—"
                state = (
                    terminal.trading_connection_status
                    if terminal.can_trade
                    else terminal.scanner_status
                )
                values = (
                    terminal.id,
                    terminal.name,
                    terminal.executable_path,
                    terminal.data_path,
                    terminal.broker,
                    terminal.catalog_id,
                    "Sí" if terminal.can_trade else "No",
                    "Sí" if terminal.can_scan else "No",
                    "Sí" if terminal.active else "No",
                    terminal.process_status,
                    expected,
                    detected,
                    terminal.account_match_status,
                    state,
                )
                for column, value in enumerate(values):
                    item = QTableWidgetItem(str(value or ""))
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                    self.table.setItem(row, column, item)
                if terminal.id == selected_id:
                    selected_row = row
            if selected_row >= 0:
                self.table.selectRow(selected_row)
        finally:
            self.table.setSortingEnabled(sorting_enabled)
        if not getattr(self.repository, "_available", lambda: True)():
            self.notice.setText(
                "Migración pendiente: ejecútela explícitamente tras un respaldo."
            )
        self._update_actions()

    def selected_terminal(self):
        row = self.table.currentRow()
        if row < 0 or self.table.item(row, 0) is None:
            return None
        return self.repository.get_by_id(
            int(self.table.item(row, 0).text())
        )

    def _update_actions(self):
        terminal = self.selected_terminal()
        selected = terminal is not None
        for button in (
            self.edit_button,
            self.state_sync_button,
            self.sync_button,
            self.toggle_button,
            self.launch_button,
            self.change_paths_button,
            self.open_data_button,
            self.diagnose_button,
            self.delete_button,
        ):
            button.setEnabled(selected)
        if terminal is not None:
            self.launch_button.setEnabled(
                terminal.active
                and Path(terminal.executable_path).is_file()
                and terminal.process_status != "RUNNING"
            )
            self.open_data_button.setEnabled(
                bool(terminal.data_path)
                and Path(terminal.data_path).is_dir()
            )
            self.toggle_button.setText(
                "Deshabilitar" if terminal.active else "Habilitar"
            )

    def _default_discovery_roots(self):
        roots = []
        for variable in ("ProgramFiles", "ProgramFiles(x86)"):
            value = os.environ.get(variable)
            if value:
                roots.append(value)
        return roots

    def detect_installations(self):
        data_root = (
            Path(os.environ.get("APPDATA", ""))
            / "MetaQuotes"
            / "Terminal"
        )
        try:
            found = self.discovery.discover(
                self._default_discovery_roots(), data_root
            )
            registered = {
                os.path.normcase(os.path.abspath(item.executable_path))
                for item in self.repository.get_all()
            }
            self._discoveries = [
                item
                for item in found
                if os.path.normcase(os.path.abspath(item.executable_path))
                not in registered
            ]
        except Exception as error:
            QMessageBox.critical(self, "Terminales MT5", str(error))
            return
        if not self._discoveries:
            QMessageBox.information(
                self,
                "Detectar instalaciones",
                "No se encontraron instalaciones nuevas.",
            )
            return
        labels = [
            f"{item.executable_path} | {item.data_path or 'Data folder no asociado'}"
            for item in self._discoveries
        ]
        selected, accepted = QInputDialog.getItem(
            self,
            "Instalaciones detectadas",
            "Seleccione una instalación para registrarla:",
            labels,
            0,
            False,
        )
        if accepted:
            self._register_dialog(
                self._discoveries[labels.index(selected)]
            )

    def register_installation(self):
        executable, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar terminal MT5",
            "",
            "MetaTrader (terminal64.exe)",
        )
        if not executable:
            return
        data_path = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta de datos"
        )
        discovery = type(
            "ManualDiscovery",
            (),
            {
                "executable_path": executable,
                "data_path": data_path,
            },
        )()
        self._register_dialog(discovery)

    def _register_dialog(self, discovery):
        dialog = MT5TerminalDialog(
            accounts=self.account_repository.get_all(), parent=self
        )
        dialog.set_paths(
            discovery.executable_path,
            getattr(discovery, "data_path", ""),
        )
        dialog.name_edit.setText(
            Path(discovery.executable_path).parent.name
        )
        if not dialog.exec():
            return
        try:
            result = self.lifecycle.register(
                dialog.terminal_value(),
                expected_account_id=dialog.selected_account_id(),
            )
            self.refresh()
            self._show_result("Terminal registrada", result)
        except Exception as error:
            self._show_error(error)

    def edit_selected(self):
        terminal = self.selected_terminal()
        if terminal is None:
            return
        accounts = self.account_repository.get_all()
        dialog = MT5TerminalDialog(
            terminal,
            accounts=accounts,
            protect_paths=True,
            parent=self,
        )
        linked = next(
            (
                account.id
                for account in accounts
                if account.mt5_terminal_id == terminal.id
            ),
            None,
        )
        if linked is not None:
            dialog.account_combo.setCurrentIndex(
                dialog.account_combo.findData(linked)
            )
        if not dialog.exec():
            return
        value = dialog.terminal_value()
        changes = {
            "name": value.name,
            "broker": value.broker,
            "catalog_id": value.catalog_id,
            "can_trade": value.can_trade,
            "can_scan": value.can_scan,
            "auto_start": value.auto_start,
        }
        try:
            result = self.lifecycle.update(terminal.id, changes)
            account_id = dialog.selected_account_id()
            if account_id is not None and account_id != linked:
                self.lifecycle.synchronize_account(
                    terminal.id,
                    "ASSOCIATE_EXISTING",
                    expected_account_id=account_id,
                    detected_login=terminal.detected_login,
                    detected_server=terminal.detected_server,
                    confirmed=True,
                )
            self.refresh()
            self._show_result("Terminal actualizada", result)
        except Exception as error:
            self._show_error(error)

    def synchronize_selected(self):
        terminal = self.selected_terminal()
        if terminal is None:
            return
        dialog = MT5AccountSyncDialog(
            terminal,
            self.account_repository.get_all(),
            self,
        )
        if not dialog.exec():
            return
        strategy = dialog.strategy()
        if strategy != "MAINTAIN":
            answer = QMessageBox.question(
                self,
                "Confirmar sincronización",
                "La cuenta solo se modificará o asociará según la acción "
                "elegida. ¿Desea continuar?",
            )
            if answer != QMessageBox.Yes:
                return
        try:
            result = self.lifecycle.synchronize_account(
                terminal.id,
                strategy,
                expected_account_id=dialog.account_id(),
                detected_login=terminal.detected_login,
                detected_server=terminal.detected_server,
                detected_broker=terminal.broker,
                new_account=(
                    dialog.new_account(terminal)
                    if strategy == "CREATE_ACCOUNT"
                    else None
                ),
                confirmed=strategy != "MAINTAIN",
            )
            self.refresh()
            self._show_result("Cuenta sincronizada", result)
        except Exception as error:
            self._show_error(error)

    def synchronize_state(self):
        terminal = self.selected_terminal()
        if terminal is None:
            return
        try:
            result = self.lifecycle.synchronize_state(terminal.id)
            self.refresh()
            self._show_result("Estado sincronizado", result)
        except Exception as error:
            self._show_error(error)

    def toggle_selected(self):
        terminal = self.selected_terminal()
        if terminal is None:
            return
        target = not terminal.active
        action = "habilitar" if target else "deshabilitar"
        if QMessageBox.question(
            self,
            "Confirmar estado",
            f"¿Desea {action} {terminal.name}?",
        ) != QMessageBox.Yes:
            return
        try:
            result = self.lifecycle.set_enabled(terminal.id, target)
            self.refresh()
            if result.success:
                self._show_result("Estado actualizado", result)
            else:
                self._show_blocked(result)
        except Exception as error:
            self._show_error(error)

    def launch_selected(self):
        terminal = self.selected_terminal()
        if terminal is None:
            return
        if QMessageBox.question(
            self,
            "Abrir terminal MT5",
            f"Kraken abrirá {terminal.name}. ¿Continuar?",
        ) != QMessageBox.Yes:
            return
        self.launch_button.setEnabled(False)
        future = self.launcher.launch_async(terminal)
        future.add_done_callback(
            lambda result: self.launchFinished.emit(terminal, result)
        )

    def change_selected_paths(self):
        terminal = self.selected_terminal()
        if terminal is None:
            return
        executable, _ = QFileDialog.getOpenFileName(
            self,
            "Cambiar ejecutable MT5",
            terminal.executable_path,
            "MetaTrader (terminal64.exe)",
        )
        if not executable:
            return
        data_path = QFileDialog.getExistingDirectory(
            self,
            "Cambiar carpeta de datos",
            terminal.data_path,
        )
        if QMessageBox.warning(
            self,
            "Confirmar cambio de rutas",
            "Cambiar rutas puede invalidar asociaciones operativas. "
            "Kraken comprobará duplicados y no modificará perfiles. "
            "¿Desea continuar?",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        ) != QMessageBox.Yes:
            return
        try:
            result = self.lifecycle.update(
                terminal.id,
                {
                    "executable_path": executable,
                    "data_path": data_path,
                },
                allow_path_change=True,
            )
            self.refresh()
            self._show_result("Rutas actualizadas", result)
        except Exception as error:
            self._show_error(error)

    def _finish_launch(self, terminal, future):
        try:
            error = future.exception()
            self.repository.set_runtime_status(
                terminal.id,
                "ERROR" if error else "RUNNING",
                None if error else future.result(),
            )
            if error:
                raise error
            QMessageBox.information(
                self, "Terminales MT5", "Terminal iniciada correctamente."
            )
        except Exception as error:
            self._show_error(error)
        finally:
            self.refresh()

    def open_data_folder(self):
        terminal = self.selected_terminal()
        if terminal is None:
            return
        if not Path(terminal.data_path).is_dir():
            QMessageBox.warning(
                self, "Terminales MT5", "La carpeta de datos no existe."
            )
            return
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(Path(terminal.data_path)))
        )

    def diagnose_selected(self):
        terminal = self.selected_terminal()
        if terminal is None:
            return
        accounts = [
            account
            for account in self.account_repository.get_all()
            if account.mt5_terminal_id == terminal.id
        ]
        expected = " / ".join(
            f"{account.login} · {account.server}" for account in accounts
        ) or "—"
        QMessageBox.information(
            self,
            "Diagnóstico MT5",
            "\n".join(
                (
                    f"Terminal: {terminal.name}",
                    f"Proceso: {terminal.process_status}",
                    f"Trading: {terminal.trading_connection_status}",
                    f"Scanner: {terminal.scanner_status}",
                    f"Cuenta esperada: {expected}",
                    "Cuenta detectada: "
                    f"{terminal.detected_login or '—'} · "
                    f"{terminal.detected_server or '—'}",
                    f"Coincidencia: {terminal.account_match_status}",
                )
            ),
        )

    def delete_selected(self):
        terminal = self.selected_terminal()
        if terminal is None:
            return
        report = self.lifecycle.dependency_report(terminal.id)
        if not report.success:
            self._show_blocked(report)
            return
        summary = (
            f"Nombre: {terminal.name}\n"
            f"Ejecutable: {terminal.executable_path}\n"
            f"Data folder: {terminal.data_path}\n\n"
            "Se eliminará únicamente el registro de Kraken. "
            "Se recomienda crear un respaldo antes de continuar."
        )
        if QMessageBox.warning(
            self,
            "Eliminar registro MT5",
            summary,
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        ) != QMessageBox.Yes:
            return
        result = self.lifecycle.delete(terminal.id, confirm=True)
        self.refresh()
        if result.success:
            self._show_result("Registro eliminado", result)
        else:
            self._show_blocked(result)

    def _show_result(self, title, result):
        details = []
        details.extend(result.warnings)
        if result.changed_fields:
            details.append(f"Cambios: {result.changed_fields}")
        QMessageBox.information(
            self, title, "\n".join(details) or "Operación completada."
        )

    def _show_blocked(self, result):
        QMessageBox.warning(
            self,
            "NO SE PUEDE COMPLETAR",
            "\n".join(f"• {item}" for item in result.blocking_reasons),
        )

    def _show_error(self, error):
        if isinstance(error, MT5TerminalLifecycleError):
            title = "Validación de terminal"
        else:
            title = "Terminales MT5"
        QMessageBox.critical(self, title, str(error))
