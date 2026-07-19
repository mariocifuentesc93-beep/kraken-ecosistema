from PySide6.QtWidgets import (
    QWidget,
    QGridLayout,
    QLabel,
    QFrame,
)


class SummaryCard(QFrame):

    def __init__(self, title):

        super().__init__()

        self.setFrameShape(QFrame.StyledPanel)

        layout = QGridLayout(self)

        self.title = QLabel(title)

        self.title.setStyleSheet("""
            color:gray;
            font-size:11px;
        """)

        self.value = QLabel("--")

        self.value.setStyleSheet("""
            font-size:18px;
            font-weight:bold;
        """)

        layout.addWidget(self.title, 0, 0)

        layout.addWidget(self.value, 1, 0)

    def set_value(self, value):

        self.value.setText(str(value))


class ProfileSummary(QWidget):

    def __init__(self):

        super().__init__()

        self.build_ui()

    # ---------------------------------------------------------

    def build_ui(self):

        layout = QGridLayout(self)

        self.mode = SummaryCard("Modo")

        self.telegram = SummaryCard("Canales")

        self.mt5 = SummaryCard("Cuentas MT5")

        self.symbols = SummaryCard("Símbolos")

        self.risk = SummaryCard("Riesgo")

        self.status = SummaryCard("Estado")

        layout.addWidget(self.mode, 0, 0)

        layout.addWidget(self.telegram, 0, 1)

        layout.addWidget(self.mt5, 0, 2)

        layout.addWidget(self.symbols, 1, 0)

        layout.addWidget(self.risk, 1, 1)

        layout.addWidget(self.status, 1, 2)

    # ---------------------------------------------------------

    def load(self, profile):

        if profile is None:

            self.mode.set_value("--")

            self.telegram.set_value("--")

            self.mt5.set_value("--")

            self.symbols.set_value("--")

            self.risk.set_value("--")

            self.status.set_value("--")

            return

        self.mode.set_value(profile.operation_mode)

        #
        # Estos valores serán reemplazados cuando
        # conectemos Telegram, MT5 y Símbolos
        #

        self.telegram.set_value("0")

        self.mt5.set_value("0")

        self.symbols.set_value("0")

        self.risk.set_value(f"{profile.risk_percent:.2f}%")

        self.status.set_value(

            "Activo" if profile.active else "Inactivo"

        )