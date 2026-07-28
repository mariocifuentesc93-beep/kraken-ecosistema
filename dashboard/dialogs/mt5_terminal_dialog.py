from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from models.mt5_terminal import MT5Terminal


class MT5TerminalDialog(QDialog):
    def __init__(
        self,
        terminal=None,
        *,
        accounts=(),
        protect_paths=True,
        parent=None,
    ):
        super().__init__(parent)
        self.terminal = terminal
        self.setWindowTitle(
            "Editar terminal MT5" if terminal else "Registrar terminal MT5"
        )
        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)
        self.name_edit = QLineEdit()
        self.executable_edit = QLineEdit()
        self.data_path_edit = QLineEdit()
        self.broker_edit = QLineEdit()
        self.catalog_combo = QComboBox()
        self.catalog_combo.setEditable(True)
        self.catalog_combo.addItems(
            ("BRIDGE_SYNTHETICS", "WELTRADE_SYNTHETICS")
        )
        self.trade_check = QCheckBox("Puede ejecutar trading")
        self.scan_check = QCheckBox("Puede leer señales Scanner")
        self.active_check = QCheckBox("Terminal habilitada")
        self.auto_start_check = QCheckBox("Autoarranque permitido")
        self.account_combo = QComboBox()
        self.account_combo.addItem("(Sin cuenta esperada)", None)
        for account in accounts:
            self.account_combo.addItem(
                f"{account.name} · {account.login} · {account.server}",
                account.id,
            )
        form.addRow("Nombre", self.name_edit)
        form.addRow("Ejecutable", self.executable_edit)
        form.addRow("Data folder", self.data_path_edit)
        form.addRow("Broker", self.broker_edit)
        form.addRow("Catálogo", self.catalog_combo)
        form.addRow("", self.trade_check)
        form.addRow("", self.scan_check)
        form.addRow("", self.active_check)
        form.addRow("", self.auto_start_check)
        form.addRow("Cuenta esperada", self.account_combo)
        self.path_notice = QLabel(
            "Las rutas están protegidas. Use “Cambiar rutas” para modificarlas."
        )
        self.path_notice.setWordWrap(True)
        layout.addWidget(self.path_notice)
        self.executable_edit.setReadOnly(bool(terminal and protect_paths))
        self.data_path_edit.setReadOnly(bool(terminal and protect_paths))
        self.active_check.setEnabled(terminal is None)
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(680, 460)
        self._load()

    def _load(self):
        terminal = self.terminal
        if terminal is None:
            self.trade_check.setChecked(True)
            self.active_check.setChecked(True)
            return
        self.name_edit.setText(terminal.name)
        self.executable_edit.setText(terminal.executable_path)
        self.data_path_edit.setText(terminal.data_path)
        self.broker_edit.setText(terminal.broker)
        index = self.catalog_combo.findText(terminal.catalog_id)
        if index < 0:
            self.catalog_combo.addItem(terminal.catalog_id)
            index = self.catalog_combo.count() - 1
        self.catalog_combo.setCurrentIndex(index)
        self.trade_check.setChecked(terminal.can_trade)
        self.scan_check.setChecked(terminal.can_scan)
        self.active_check.setChecked(terminal.active)
        self.auto_start_check.setChecked(terminal.auto_start)

    def set_paths(self, executable_path, data_path=""):
        self.executable_edit.setText(str(executable_path or ""))
        self.data_path_edit.setText(str(data_path or ""))

    def selected_account_id(self):
        return self.account_combo.currentData()

    def terminal_value(self):
        original = self.terminal or MT5Terminal()
        return MT5Terminal(
            id=original.id,
            name=self.name_edit.text().strip(),
            executable_path=self.executable_edit.text().strip(),
            data_path=self.data_path_edit.text().strip(),
            broker=self.broker_edit.text().strip(),
            catalog_id=self.catalog_combo.currentText().strip(),
            can_trade=self.trade_check.isChecked(),
            can_scan=self.scan_check.isChecked(),
            active=self.active_check.isChecked(),
            portable=original.portable,
            auto_start=self.auto_start_check.isChecked(),
            process_id=original.process_id,
            connection_status=original.connection_status,
            process_status=original.process_status,
            trading_connection_status=original.trading_connection_status,
            scanner_status=original.scanner_status,
            account_match_status=original.account_match_status,
            detected_login=original.detected_login,
            detected_server=original.detected_server,
        )


class MT5AccountSyncDialog(QDialog):
    def __init__(self, terminal, accounts=(), parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sincronizar cuenta MT5")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)
        expected = [
            account
            for account in accounts
            if account.mt5_terminal_id == terminal.id
        ]
        self.accounts = list(accounts)
        self.expected_combo = QComboBox()
        self.expected_combo.addItem("(Ninguna)", None)
        for account in accounts:
            self.expected_combo.addItem(
                f"{account.name} · {account.login} · {account.server}",
                account.id,
            )
        if expected:
            self.expected_combo.setCurrentIndex(
                self.expected_combo.findData(expected[0].id)
            )
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItem(
            "Mantener cuenta esperada actual", "MAINTAIN"
        )
        self.strategy_combo.addItem(
            "Actualizar la cuenta esperada con la detectada",
            "UPDATE_EXPECTED",
        )
        self.strategy_combo.addItem(
            "Registrar la cuenta detectada como nueva", "CREATE_ACCOUNT"
        )
        self.strategy_combo.addItem(
            "Asociar una cuenta existente", "ASSOCIATE_EXISTING"
        )
        self.account_name = QLineEdit(
            f"MT5 {terminal.detected_login or ''}".strip()
        )
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        form.addRow("Login esperado", QLabel(
            " / ".join(str(item.login) for item in expected) or "—"
        ))
        form.addRow("Login detectado", QLabel(
            str(terminal.detected_login or "—")
        ))
        form.addRow("Servidor esperado", QLabel(
            " / ".join(item.server for item in expected) or "—"
        ))
        form.addRow("Servidor detectado", QLabel(
            str(terminal.detected_server or "—")
        ))
        form.addRow("Broker esperado", QLabel(terminal.broker or "—"))
        form.addRow("Broker detectado", QLabel(
            "No disponible en el diagnóstico actual"
        ))
        form.addRow("Acción", self.strategy_combo)
        form.addRow("Cuenta existente", self.expected_combo)
        form.addRow("Nombre nueva cuenta", self.account_name)
        form.addRow("Contraseña nueva cuenta", self.password)
        notice = QLabel(
            "Nada se sobrescribe automáticamente. La acción elegida requiere "
            "confirmación al guardar."
        )
        notice.setWordWrap(True)
        layout.addWidget(notice)
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(620, 420)

    def strategy(self):
        return self.strategy_combo.currentData()

    def account_id(self):
        return self.expected_combo.currentData()

    def new_account(self, terminal):
        return MT5Account(
            name=self.account_name.text().strip()
            or f"MT5 {terminal.detected_login}",
            login=int(terminal.detected_login or 0),
            password=self.password.text(),
            server=str(terminal.detected_server or ""),
            terminal_path=terminal.executable_path,
            mt5_terminal_id=terminal.id,
            execution_mode="OFF",
        )
