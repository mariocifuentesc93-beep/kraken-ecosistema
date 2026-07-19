from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)


class TelegramTab(QWidget):

    def __init__(self):

        super().__init__()

        self.profile = None

        self.build_ui()

    # ---------------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        title = QLabel("Configuración de Telegram")

        title.setStyleSheet("""
            font-size:18px;
            font-weight:bold;
        """)

        layout.addWidget(title)

        # -------------------------------------------------

        account_layout = QHBoxLayout()

        account_layout.addWidget(QLabel("Cuenta Telegram"))

        self.account = QComboBox()

        account_layout.addWidget(self.account)

        layout.addLayout(account_layout)

        # -------------------------------------------------

        self.channels = QTableWidget()

        self.channels.setColumnCount(4)

        self.channels.setHorizontalHeaderLabels([

            "Activo",

            "Canal",

            "Chat ID",

            "Prioridad"

        ])

        self.channels.horizontalHeader().setSectionResizeMode(

            QHeaderView.Stretch

        )

        layout.addWidget(self.channels)

        # -------------------------------------------------

        buttons = QHBoxLayout()

        self.add = QPushButton("➕ Agregar")

        self.edit = QPushButton("✏ Editar")

        self.delete = QPushButton("🗑 Eliminar")

        self.refresh = QPushButton("🔄 Actualizar")

        buttons.addWidget(self.add)

        buttons.addWidget(self.edit)

        buttons.addWidget(self.delete)

        buttons.addStretch()

        buttons.addWidget(self.refresh)

        layout.addLayout(buttons)

    # ---------------------------------------------------------

    def load(self, profile):

        self.profile = profile

        self.reload()

    # ---------------------------------------------------------

    def reload(self):

        self.channels.setRowCount(0)

        if self.profile is None:

            return

        #
        # Próximo paso:
        # cargar cuentas Telegram desde la BD
        #

        self.account.clear()

        #
        # Próximo paso:
        # cargar canales asociados al perfil
        #