from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QCheckBox,
    QPushButton,
    QSpinBox,
    QFileDialog,
    QHBoxLayout,
)


class MT5AccountDialog(QDialog):

    def __init__(self, account=None, parent=None):

        super().__init__(parent)

        self.account = account

        self.setWindowTitle("Cuenta MT5")

        self.resize(600, 520)

        self.build_ui()

        if account:

            self.load_account()

    # ---------------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.name = QLineEdit()

        self.login = QLineEdit()

        self.password = QLineEdit()

        self.password.setEchoMode(QLineEdit.Password)

        self.server = QLineEdit()

        # -----------------------------------------------------

        path_layout = QHBoxLayout()

        self.terminal = QLineEdit()

        self.browse = QPushButton("...")

        self.browse.clicked.connect(self.select_terminal)

        path_layout.addWidget(self.terminal)

        path_layout.addWidget(self.browse)

        # -----------------------------------------------------

        self.magic = QSpinBox()

        self.magic.setMaximum(999999999)

        self.magic.setValue(10001)

        self.active = QCheckBox()

        self.active.setChecked(True)

        self.auto_connect = QCheckBox()

        self.auto_connect.setChecked(True)

        self.reconnect = QCheckBox()

        self.reconnect.setChecked(True)

        self.description = QTextEdit()

        self.description.setFixedHeight(100)

        form.addRow("Nombre", self.name)

        form.addRow("Login", self.login)

        form.addRow("Contraseña", self.password)

        form.addRow("Servidor", self.server)

        form.addRow("Terminal MT5", path_layout)

        form.addRow("Magic Number", self.magic)

        form.addRow("Activa", self.active)

        form.addRow("Auto conectar", self.auto_connect)

        form.addRow("Reconectar", self.reconnect)

        form.addRow("Descripción", self.description)

        layout.addLayout(form)

        # -----------------------------------------------------

        buttons = QHBoxLayout()

        self.test = QPushButton("Probar conexión")

        self.save = QPushButton("Guardar")

        self.cancel = QPushButton("Cancelar")

        self.save.clicked.connect(self.accept)

        self.cancel.clicked.connect(self.reject)

        buttons.addWidget(self.test)

        buttons.addStretch()

        buttons.addWidget(self.save)

        buttons.addWidget(self.cancel)

        layout.addLayout(buttons)

    # ---------------------------------------------------------

    def select_terminal(self):

        filename, _ = QFileDialog.getOpenFileName(

            self,

            "Seleccionar terminal MT5",

            "",

            "Executable (*.exe)"

        )

        if filename:

            self.terminal.setText(filename)

    # ---------------------------------------------------------

    def load_account(self):

        self.name.setText(self.account.name)

        self.login.setText(str(self.account.login))

        self.password.setText(self.account.password)

        self.server.setText(self.account.server)

        self.terminal.setText(self.account.terminal_path)

        self.magic.setValue(self.account.magic_number)

        self.active.setChecked(self.account.active)

        self.auto_connect.setChecked(self.account.auto_connect)

        self.reconnect.setChecked(self.account.reconnect)

        self.description.setPlainText(self.account.description)

    # ---------------------------------------------------------

    def get_data(self):

        return {

            "name": self.name.text().strip(),

            "login": int(self.login.text()) if self.login.text() else 0,

            "password": self.password.text(),

            "server": self.server.text().strip(),

            "terminal_path": self.terminal.text().strip(),

            "magic_number": self.magic.value(),

            "active": self.active.isChecked(),

            "auto_connect": self.auto_connect.isChecked(),

            "reconnect": self.reconnect.isChecked(),

            "description": self.description.toPlainText().strip(),

        }