from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QPushButton,
    QCheckBox,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QListWidget,
    QListWidgetItem,
    QFormLayout,
)

from dashboard.widgets.section_widget import SectionWidget
from dashboard.dialogs.dialog_layout import fit_dialog_to_screen


class DashboardPreferencesDialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Preferencias del Dashboard")

        fit_dialog_to_screen(self, 1200, 700)

        self.build_ui()

    # ----------------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()

        layout.addWidget(self.tabs)

        self.build_widgets_tab()

        self.build_layout_tab()

        self.build_refresh_tab()

        self.build_alerts_tab()

        self.build_theme_tab()

        self.build_profiles_tab()

        buttons = QHBoxLayout()

        buttons.addStretch()

        self.btnDefaults = QPushButton("Restaurar")

        self.btnSave = QPushButton("Guardar")

        self.btnCancel = QPushButton("Cancelar")

        buttons.addWidget(self.btnDefaults)

        buttons.addWidget(self.btnSave)

        buttons.addWidget(self.btnCancel)

        layout.addLayout(buttons)

        self.btnSave.clicked.connect(
            self.accept
        )

        self.btnCancel.clicked.connect(
            self.reject
        )

    def build_widgets_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget("Widgets visibles")

        self.lstWidgets = QListWidget()

        widgets = [

            "Dashboard",

            "Operaciones",

            "Estadísticas",

            "Calendario",

            "Símbolos",

            "Logs",

            "Telegram",

            "MT5",

            "Riesgo",

            "Noticias",

            "Alertas",

            "Perfiles"

        ]

        for name in widgets:

            item = QListWidgetItem(name)

            item.setCheckState(
                item.CheckState.Checked
            )

            self.lstWidgets.addItem(item)

        section.addWidget(self.lstWidgets)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Widgets"
        )

    def build_layout_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget("Distribución")

        form = QFormLayout()

        self.cboLayout = QComboBox()

        self.cboLayout.addItems([

            "Clásico",

            "Trading",

            "Compacto",

            "Pantalla Completa",

            "Personalizado"

        ])

        self.spnColumns = QSpinBox()

        self.spnColumns.setRange(1, 6)

        self.chkRemember = QCheckBox(
            "Recordar posición"
        )

        form.addRow(
            "Diseño",
            self.cboLayout
        )

        form.addRow(
            "Columnas",
            self.spnColumns
        )

        form.addRow(
            "",
            self.chkRemember
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Diseño"
        )

    def build_refresh_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget("Actualización")

        form = QFormLayout()

        self.spnRefresh = QSpinBox()

        self.spnRefresh.setRange(
            100,
            10000
        )

        self.spnRefresh.setValue(1000)

        self.chkRealtime = QCheckBox(
            "Tiempo real"
        )

        self.chkAnimations = QCheckBox(
            "Animaciones"
        )

        form.addRow(
            "Intervalo (ms)",
            self.spnRefresh
        )

        form.addRow(
            "",
            self.chkRealtime
        )

        form.addRow(
            "",
            self.chkAnimations
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Actualización"
        )

    def build_alerts_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget("Alertas")

        form = QFormLayout()

        self.chkPopup = QCheckBox(
            "Mostrar popup"
        )

        self.chkSound = QCheckBox(
            "Sonido"
        )

        self.chkCritical = QCheckBox(
            "Solo críticas"
        )

        self.spnSeconds = QSpinBox()

        self.spnSeconds.setValue(5)

        form.addRow(
            "",
            self.chkPopup
        )

        form.addRow(
            "",
            self.chkSound
        )

        form.addRow(
            "",
            self.chkCritical
        )

        form.addRow(
            "Duración",
            self.spnSeconds
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Alertas"
        )

    def build_theme_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget("Tema")

        form = QFormLayout()

        self.cboTheme = QComboBox()

        self.cboTheme.addItems([

            "Oscuro",

            "Claro",

            "Sistema"

        ])

        self.cboAccent = QComboBox()

        self.cboAccent.addItems([

            "Verde Kraken",

            "Azul",

            "Rojo",

            "Naranja",

            "Morado"

        ])

        self.spnScale = QDoubleSpinBox()

        self.spnScale.setRange(
            0.5,
            2.0
        )

        self.spnScale.setSingleStep(0.1)

        self.spnScale.setValue(1.0)

        form.addRow(
            "Tema",
            self.cboTheme
        )

        form.addRow(
            "Color",
            self.cboAccent
        )

        form.addRow(
            "Escala",
            self.spnScale
        )

        section.addLayout(form)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Tema"
        )

    def build_profiles_tab(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        section = SectionWidget(
            "Perfiles visuales"
        )

        self.lstProfiles = QListWidget()

        section.addWidget(
            self.lstProfiles
        )

        buttons = QHBoxLayout()

        self.btnNew = QPushButton("Nuevo")

        self.btnDuplicate = QPushButton("Duplicar")

        self.btnDelete = QPushButton("Eliminar")

        buttons.addWidget(self.btnNew)

        buttons.addWidget(self.btnDuplicate)

        buttons.addWidget(self.btnDelete)

        section.addLayout(buttons)

        layout.addWidget(section)

        layout.addStretch()

        self.tabs.addTab(
            page,
            "Perfiles"
        )

    def get_preferences(self):

        widgets = []

        for i in range(self.lstWidgets.count()):

            item = self.lstWidgets.item(i)

            if item.checkState():

                widgets.append(
                    item.text()
                )

        return {

            "widgets": widgets,

            "layout": self.cboLayout.currentText(),

            "columns": self.spnColumns.value(),

            "remember_layout": self.chkRemember.isChecked(),

            "refresh": self.spnRefresh.value(),

            "realtime": self.chkRealtime.isChecked(),

            "animations": self.chkAnimations.isChecked(),

            "popup": self.chkPopup.isChecked(),

            "sound": self.chkSound.isChecked(),

            "critical_only": self.chkCritical.isChecked(),

            "duration": self.spnSeconds.value(),

            "theme": self.cboTheme.currentText(),

            "accent": self.cboAccent.currentText(),

            "scale": self.spnScale.value()

        }

