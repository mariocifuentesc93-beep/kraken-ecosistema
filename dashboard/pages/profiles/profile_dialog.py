from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QCheckBox,
    QPushButton,
    QColorDialog,
    QHBoxLayout,
    QMessageBox,
)


class ProfileDialog(QDialog):

    def __init__(self, profile=None, parent=None):

        super().__init__(parent)

        self.profile = profile

        self.setWindowTitle("Perfil")

        self.resize(520, 430)

        self.build_ui()

        if profile is not None:

            self.load_profile()

    # ---------------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.name = QLineEdit()

        self.description = QTextEdit()

        self.description.setFixedHeight(80)

        self.mode = QComboBox()

        self.mode.addItems([

            "telegram",

            "manual",

            "both",

        ])

        self.icon = QLineEdit("📈")

        self.color = QPushButton("#00C853")

        self.color.clicked.connect(

            self.pick_color

        )

        self.active = QCheckBox()

        self.active.setChecked(True)

        form.addRow("Nombre", self.name)

        form.addRow("Descripción", self.description)

        form.addRow("Modo", self.mode)

        form.addRow("Icono", self.icon)

        form.addRow("Color", self.color)

        form.addRow("Activo", self.active)

        layout.addLayout(form)

        buttons = QHBoxLayout()

        buttons.addStretch()

        self.save = QPushButton("Guardar")

        self.cancel = QPushButton("Cancelar")

        self.save.clicked.connect(

            self.validate_and_accept

        )

        self.cancel.clicked.connect(

            self.reject

        )

        buttons.addWidget(self.save)

        buttons.addWidget(self.cancel)

        layout.addLayout(buttons)

    # ---------------------------------------------------------

    def pick_color(self):

        color = QColorDialog.getColor()

        if color.isValid():

            self.color.setText(

                color.name()

            )

    # ---------------------------------------------------------

    def load_profile(self):

        self.name.setText(

            getattr(self.profile, "name", "")

        )

        self.description.setPlainText(

            getattr(self.profile, "description", "")

        )

        self.mode.setCurrentText(

            getattr(

                self.profile,

                "operation_mode",

                "telegram",

            )

        )

        self.icon.setText(

            getattr(

                self.profile,

                "icon",

                "📈",

            )

        )

        self.color.setText(

            getattr(

                self.profile,

                "color",

                "#00C853",

            )

        )

        self.active.setChecked(

            getattr(

                self.profile,

                "active",

                True,

            )

        )

    # ---------------------------------------------------------

    def validate_and_accept(self):

        if not self.name.text().strip():

            QMessageBox.warning(

                self,

                "Perfil",

                "Debe ingresar un nombre.",

            )

            return

        self.accept()

    # ---------------------------------------------------------

    def get_data(self):

        return {

            "name": self.name.text().strip(),

            "description": self.description.toPlainText().strip(),

            "operation_mode": self.mode.currentText(),

            "icon": self.icon.text().strip() or "📈",

            "color": self.color.text(),

            "active": self.active.isChecked(),

        }