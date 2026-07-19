from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QHBoxLayout,
)

from dashboard.styles import *


class TopBar(QWidget):

    def __init__(self):

        super().__init__()

        self.setFixedHeight(70)

        self.setStyleSheet(f"""
            background:{PANEL_COLOR};
            border-bottom:1px solid {BORDER_COLOR};
        """)

        self.build_ui()

        self.timer = QTimer(self)

        self.timer.timeout.connect(self.update_clock)

        self.timer.start(1000)

        self.update_clock()

    # ---------------------------------------------------------

    def build_ui(self):

        layout = QHBoxLayout(self)

        layout.setContentsMargins(20, 10, 20, 10)

        self.logo = QLabel("🐙 Kraken Bot")

        self.logo.setStyleSheet(f"""
            color:{TEXT_COLOR};
            font-size:22px;
            font-weight:bold;
        """)

        layout.addWidget(self.logo)

        layout.addStretch()

        self.profile = QLabel("Perfil: Ninguno")

        self.profile.setStyleSheet(f"""
            color:{TEXT_COLOR};
            font-size:12px;
        """)

        layout.addWidget(self.profile)

        layout.addSpacing(30)

        self.telegram = QLabel("🔴 Telegram")

        self.telegram.setStyleSheet(f"""
            color:{TEXT_COLOR};
            font-size:12px;
        """)

        layout.addWidget(self.telegram)

        layout.addSpacing(20)

        self.mt5 = QLabel("🔴 MT5")

        self.mt5.setStyleSheet(f"""
            color:{TEXT_COLOR};
            font-size:12px;
        """)

        layout.addWidget(self.mt5)

        layout.addSpacing(20)

        self.engine = QLabel("🔴 Engine")

        self.engine.setStyleSheet(f"""
            color:{TEXT_COLOR};
            font-size:12px;
        """)

        layout.addWidget(self.engine)

        layout.addSpacing(20)

        self.clock = QLabel()

        self.clock.setAlignment(Qt.AlignCenter)

        self.clock.setStyleSheet(f"""
            color:{TEXT_COLOR};
            font-size:13px;
            font-weight:bold;
        """)

        layout.addWidget(self.clock)

    # ---------------------------------------------------------

    def update_clock(self):

        self.clock.setText(

            datetime.now().strftime(

                "%d/%m/%Y %H:%M:%S"

            )

        )

    # ---------------------------------------------------------

    def set_profile(self, name):

        self.profile.setText(

            f"Perfil: {name}"

        )

    # ---------------------------------------------------------

    def set_telegram_status(self, connected):

        self.telegram.setText(

            "🟢 Telegram" if connected else "🔴 Telegram"

        )

    # ---------------------------------------------------------

    def set_mt5_status(self, connected):

        self.mt5.setText(

            "🟢 MT5" if connected else "🔴 MT5"

        )

    # ---------------------------------------------------------

    def set_engine_status(self, running):

        self.engine.setText(

            "🟢 Engine" if running else "🔴 Engine"

        )