from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
)


class ProfileHeader(QWidget):

    def __init__(self):

        super().__init__()

        self.build_ui()

    # ---------------------------------------------------------

    def build_ui(self):

        root = QHBoxLayout(self)

        self.icon = QLabel("📈")

        self.icon.setStyleSheet("""
            font-size:40px;
        """)

        info = QVBoxLayout()

        self.name = QLabel("Perfiles Activos")

        self.name.setStyleSheet("""
            font-size:22px;
            font-weight:bold;
        """)

        self.description = QLabel(
            "Seleccione un perfil para comenzar."
        )

        self.description.setStyleSheet("""
            color:gray;
            font-size:12px;
        """)

        self.mode = QLabel()

        self.mode.setStyleSheet("""
            color:#00C853;
            font-size:12px;
        """)

        info.addWidget(self.name)

        info.addWidget(self.description)

        info.addWidget(self.mode)

        root.addWidget(self.icon)

        root.addLayout(info)

        root.addStretch()

        line = QFrame()

        line.setFrameShape(QFrame.HLine)

    # ---------------------------------------------------------

    def set_profile(self, profile):

        if profile is None:

            self.name.setText("Perfiles Activos")

            self.description.setText(
                "Seleccione un perfil."
            )

            self.icon.setText("📈")

            self.mode.setText("")

            return

        self.icon.setText(profile.icon)

        self.name.setText(profile.name)

        self.description.setText(profile.description)

        if profile.operation_mode == "telegram":

            self.mode.setText("Modo: Telegram")

        elif profile.operation_mode == "manual":

            self.mode.setText("Modo: Manual")

        else:

            self.mode.setText("Modo: Telegram + Manual")