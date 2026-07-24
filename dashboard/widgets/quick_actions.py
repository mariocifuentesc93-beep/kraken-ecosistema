from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QGridLayout,
)

from dashboard.styles import (
    card_style,
    title_style,
)
from dashboard.icons import ICON_COLOR, ICON_INFO, colored_icon


class QuickActions(QWidget):

    action_requested = Signal(str)

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setStyleSheet(card_style())

        self.setMinimumHeight(220)

        self.buttons = {}

        self.build_ui()

    # ---------------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(15, 15, 15, 15)

        layout.setSpacing(12)

        title = QLabel("Acciones rápidas")

        title.setStyleSheet(title_style())

        title.setAlignment(Qt.AlignLeft)

        layout.addWidget(title)

        grid = QGridLayout()

        grid.setHorizontalSpacing(10)

        grid.setVerticalSpacing(10)

        actions = [

            ("Nuevo Perfil", "profiles", "users"),
            ("Telegram", "telegram", "send"),
            ("MT5", "mt5", "activity"),
            ("Trading", "trading", "briefcase-business"),
            ("Analytics", "analytics", "chart-spline"),
            ("Configuración", "settings", "settings"),
            ("Reportes", "reports", "folder-open"),
            ("Logs", "logs", "scroll-text"),

        ]

        row = 0

        col = 0

        for text, action, icon_name in actions:

            button = QPushButton(text)
            button.setIcon(colored_icon(icon_name, ICON_INFO if action in ("telegram", "analytics") else ICON_COLOR))

            button.setMinimumHeight(45)

            button.clicked.connect(

                lambda _, a=action: self.action_requested.emit(a)

            )

            grid.addWidget(button, row, col)

            self.buttons[action] = button

            col += 1

            if col >= 2:

                col = 0

                row += 1

        layout.addLayout(grid)

        layout.addStretch()

    # ---------------------------------------------------------

    def enable_action(self, action, enabled=True):

        button = self.buttons.get(action)

        if button:

            button.setEnabled(enabled)

    # ---------------------------------------------------------

    def set_action_text(self, action, text):

        button = self.buttons.get(action)

        if button:

            button.setText(text)

    # ---------------------------------------------------------

    def get_button(self, action):

        return self.buttons.get(action)
