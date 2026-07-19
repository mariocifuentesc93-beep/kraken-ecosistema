from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QCheckBox,
    QPushButton,
    QColorDialog,
    QMessageBox,
)

from controllers.profile_controller import profile_controller


class GeneralTab(QWidget):

    def __init__(self):

        super().__init__()

        self.profile = None

        self.build_ui()

    # ---------------------------------------------------------

    def build_ui(self):

        layout = QFormLayout(self)

        self.name = QLineEdit()

        self.description = QTextEdit()

        self.description.setFixedHeight(90)

        self.icon = QLineEdit()

        self.color = QPushButton("#00C853")

        self.mode = QComboBox()

        self.mode.addItems([

            "telegram",

            "manual",

            "both"

        ])

        self.active = QCheckBox("Perfil activo")

        self.active.setChecked(True)

        self.save = QPushButton("💾 Guardar cambios")

        self.color.clicked.connect(self.select_color)

        self.save.clicked.connect(self.save_profile)

        layout.addRow("Nombre", self.name)

        layout.addRow("Descripción", self.description)

        layout.addRow("Icono", self.icon)

        layout.addRow("Color", self.color)

        layout.addRow("Modo", self.mode)

        layout.addRow("", self.active)

        layout.addRow("", self.save)

    # ---------------------------------------------------------

    def load(self, profile):

        self.profile = profile

        if profile is None:

            return

        self.name.setText(profile.name)

        self.description.setPlainText(profile.description)

        self.icon.setText(profile.icon)

        self.color.setText(profile.color)

        self.mode.setCurrentText(profile.operation_mode)

        self.active.setChecked(profile.active)

    # ---------------------------------------------------------

    def select_color(self):

        color = QColorDialog.getColor()

        if color.isValid():

            self.color.setText(color.name())

    # ---------------------------------------------------------

    def save_profile(self):

        if self.profile is None:

            return

        self.profile.name = self.name.text().strip()

        self.profile.description = self.description.toPlainText().strip()

        self.profile.icon = self.icon.text().strip()

        self.profile.color = self.color.text()

        self.profile.operation_mode = self.mode.currentText()

        self.profile.active = self.active.isChecked()

        self.profile.enabled = self.active.isChecked()

        profile_controller.update(self.profile)

        parent = self.parent()

        while parent:

            if hasattr(parent, "refresh_profile"):

                parent.refresh_profile()

                break

            parent = parent.parent()

        QMessageBox.information(

            self,

            "Perfil",

            "Perfil actualizado correctamente."

        )