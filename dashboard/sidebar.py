from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QFrame,
)

from dashboard.styles import *


class SideBar(QWidget):

    page_selected = Signal(str)

    def __init__(self):

        super().__init__()

        self.setFixedWidth(250)

        self.setStyleSheet(f"""
            background:{PANEL_COLOR};
        """)

        self.button_widgets = {}

        self.current_page = None

        self.build_ui()

    # ---------------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(10, 15, 10, 15)

        layout.setSpacing(6)

        logo = QLabel("🐙 Kraken Bot")

        logo.setAlignment(Qt.AlignCenter)

        logo.setStyleSheet(f"""
            color:{TEXT_COLOR};
            font-size:20px;
            font-weight:bold;
            padding:12px;
        """)

        layout.addWidget(logo)

        line = QFrame()

        line.setFrameShape(QFrame.HLine)

        line.setStyleSheet(f"""
            color:{BUTTON_HOVER};
        """)

        layout.addWidget(line)

        self.pages = [

            ("home", "🏠 Dashboard"),

            ("profiles", "👤 Perfiles"),

            ("telegram", "📱 Telegram"),

            ("mt5", "💹 MT5"),

            ("channels", "📡 Canales"),

            ("risk", "⚠ Gestión de Riesgo"),

            ("trading", "📈 Trading"),

            ("kraken_analytics", "📊 Kraken Analytics"),

            ("mt5_analytics", "📈 MT5 Analytics"),

            ("calendar", "📅 Calendario"),

            ("journal", "📓 Trading Journal"),

            ("goals", "🎯 Objetivos"),

            ("reports", "📄 Reportes"),

            ("ai", "🤖 Inteligencia Artificial"),

            ("settings", "⚙ Configuración"),

            ("logs", "📜 Logs"),

        ]

        for page, text in self.pages:

            button = QPushButton(text)

            button.setCursor(Qt.PointingHandCursor)

            button.clicked.connect(

                lambda _, p=page: self.select_page(p)

            )

            layout.addWidget(button)

            self.button_widgets[page] = button

        layout.addStretch()

        version = QLabel("Kraken Bot v1.0 Alpha")

        version.setAlignment(Qt.AlignCenter)

        version.setStyleSheet("""
            color:gray;
            font-size:11px;
            padding:8px;
        """)

        layout.addWidget(version)

        self.select_page("home")

    # ---------------------------------------------------------

    def select_page(self, page):

        self.current_page = page

        self.refresh_buttons()

        self.page_selected.emit(page)

    # ---------------------------------------------------------

    def refresh_buttons(self):

        normal = f"""
        QPushButton {{
            background:{BUTTON_COLOR};
            color:{TEXT_COLOR};
            border:none;
            border-radius:8px;
            padding-left:15px;
            text-align:left;
            font-size:13px;
            min-height:42px;
        }}

        QPushButton:hover {{
            background:{BUTTON_HOVER};
        }}
        """

        selected = f"""
        QPushButton {{
            background:{ACCENT_COLOR};
            color:white;
            border:none;
            border-radius:8px;
            padding-left:15px;
            text-align:left;
            font-size:13px;
            font-weight:bold;
            min-height:42px;
        }}
        """

        for page, button in self.button_widgets.items():

            if page == self.current_page:

                button.setStyleSheet(selected)

            else:

                button.setStyleSheet(normal)