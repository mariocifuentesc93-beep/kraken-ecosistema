from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QPushButton,
    QHBoxLayout,
)


class ProfileToolbar(QWidget):

    new_clicked = Signal()

    edit_clicked = Signal()

    duplicate_clicked = Signal()

    activate_clicked = Signal()

    deactivate_clicked = Signal()

    delete_clicked = Signal()

    refresh_clicked = Signal()


    def __init__(self):

        super().__init__()

        self.build_ui()


    # ---------------------------------------------------------

    def build_ui(self):

        layout = QHBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        self.new = QPushButton("➕ Nuevo")

        self.edit = QPushButton("✏ Editar")

        self.duplicate = QPushButton("📄 Duplicar")

        self.activate = QPushButton("✔ Activar")

        self.deactivate = QPushButton("🔴 Desactivar")

        self.delete = QPushButton("🗑 Eliminar")

        self.refresh = QPushButton("🔄 Actualizar")


        layout.addWidget(self.new)

        layout.addWidget(self.edit)

        layout.addWidget(self.duplicate)

        layout.addWidget(self.activate)

        layout.addWidget(self.deactivate)

        layout.addWidget(self.delete)

        layout.addStretch()

        layout.addWidget(self.refresh)


        self.new.clicked.connect(

            self.new_clicked.emit

        )

        self.edit.clicked.connect(

            self.edit_clicked.emit

        )

        self.duplicate.clicked.connect(

            self.duplicate_clicked.emit

        )

        self.activate.clicked.connect(

            self.activate_clicked.emit

        )

        self.deactivate.clicked.connect(

            self.deactivate_clicked.emit

        )

        self.delete.clicked.connect(

            self.delete_clicked.emit

        )

        self.refresh.clicked.connect(

            self.refresh_clicked.emit

        )