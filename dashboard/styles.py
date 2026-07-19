# ============================================================
# KRAKEN BOT UI THEME
# ============================================================

FONT = "Segoe UI"

# ============================================================
# COLORES
# ============================================================

PRIMARY_COLOR = "#00C853"
ACCENT_COLOR = "#00E676"

BACKGROUND_COLOR = "#1B1D22"
PANEL_COLOR = "#252932"
CARD_COLOR = "#2E3440"

BUTTON_COLOR = "#363D4D"
BUTTON_HOVER = "#465066"
BUTTON_PRESSED = "#00C853"

TEXT_COLOR = "#FFFFFF"
SECONDARY_TEXT = "#B0BEC5"

SUCCESS_COLOR = "#00C853"
WARNING_COLOR = "#FFC107"
ERROR_COLOR = "#E53935"
INFO_COLOR = "#29B6F6"

BORDER_COLOR = "#3B4252"

# ============================================================
# TAMAÑOS
# ============================================================

RADIUS = 10
PADDING = 10
SPACING = 10

TITLE_SIZE = 18
TEXT_SIZE = 11
VALUE_SIZE = 22

# ============================================================
# TARJETAS
# ============================================================

def card_style():

    return f"""
    QWidget {{
        background:{CARD_COLOR};
        border:1px solid {BORDER_COLOR};
        border-radius:{RADIUS}px;
    }}
    """


# ============================================================
# BOTONES
# ============================================================

def button_style():

    return f"""
    QPushButton {{
        background:{BUTTON_COLOR};
        color:{TEXT_COLOR};
        border:none;
        border-radius:8px;
        padding:8px;
        font-size:{TEXT_SIZE + 1}px;
    }}

    QPushButton:hover {{
        background:{BUTTON_HOVER};
    }}

    QPushButton:pressed {{
        background:{BUTTON_PRESSED};
    }}

    QPushButton:disabled {{
        color:#777777;
        background:#30343C;
    }}
    """


# ============================================================
# LABELS
# ============================================================

def title_style():

    return f"""
    color:{TEXT_COLOR};
    font-size:{TITLE_SIZE}px;
    font-weight:bold;
    """


def subtitle_style():

    return f"""
    color:{SECONDARY_TEXT};
    font-size:{TEXT_SIZE}px;
    """


def value_style():

    return f"""
    color:{PRIMARY_COLOR};
    font-size:{VALUE_SIZE}px;
    font-weight:bold;
    """


def status_style(color):

    return f"""
    color:{color};
    font-size:{TEXT_SIZE}px;
    font-weight:bold;
    """


# ============================================================
# TABLAS
# ============================================================

def table_style():

    return f"""
    QTableView, QTableWidget {{
        background:{CARD_COLOR}; color:{TEXT_COLOR};
        border:1px solid {BORDER_COLOR}; border-radius:7px;
        gridline-color:#343C49; alternate-background-color:#292F39;
        selection-background-color:#1E4F78; selection-color:{TEXT_COLOR};
        outline:0;
    }}
    QTableView::item, QTableWidget::item {{
        background:{CARD_COLOR}; color:{TEXT_COLOR}; padding:6px;
        border:0; border-bottom:1px solid #343C49;
    }}
    QTableView::item:alternate, QTableWidget::item:alternate {{ background:#292F39; color:{TEXT_COLOR}; }}
    QTableView::item:hover, QTableWidget::item:hover {{ background:#364252; color:{TEXT_COLOR}; }}
    QTableView::item:selected, QTableWidget::item:selected {{ background:#1E4F78; color:{TEXT_COLOR}; }}
    QTableView::item:disabled, QTableWidget::item:disabled {{ background:#242A33; color:#AAB3BE; }}
    QTableView:disabled, QTableWidget:disabled {{ background:#242A33; color:#AAB3BE; }}
    QTableCornerButton::section {{ background:{PANEL_COLOR}; border:0; border-right:1px solid {BORDER_COLOR}; border-bottom:1px solid {BORDER_COLOR}; }}
    QHeaderView {{ background:{PANEL_COLOR}; }}
    QHeaderView::section {{ background:#20252E; color:{TEXT_COLOR}; border:0; border-right:1px solid {BORDER_COLOR}; border-bottom:1px solid {BORDER_COLOR}; padding:7px; font-weight:700; }}
    QHeaderView::section:hover {{ background:#2E3947; color:{TEXT_COLOR}; }}
    """


# ============================================================
# INPUTS
# ============================================================

def input_style():

    return f"""
    QLineEdit,
    QTextEdit,
    QPlainTextEdit,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox {{
        background:{BUTTON_COLOR};
        color:{TEXT_COLOR};
        border:1px solid {BORDER_COLOR};
        border-radius:6px;
        padding:6px;
    }}

    QLineEdit:focus,
    QTextEdit:focus,
    QComboBox:focus {{
        border:1px solid {ACCENT_COLOR};
    }}
    """
