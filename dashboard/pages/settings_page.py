from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
    QCheckBox,
    QPushButton,
    QMessageBox,
)

from repositories.settings_repository import settings_repository
from dashboard.ui_theme import set_visual_role


class SettingsPage(QWidget):

    def __init__(self):

        super().__init__()

        self.build_ui()

        self.load()

    # ======================================================

    def build_ui(self):

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # ==================================================
        # EJECUCIÓN
        # ==================================================

        execution_box = QGroupBox("Modo de ejecución")

        execution_layout = QGridLayout(execution_box)

        self.cbo_execution = QComboBox()

        self.cbo_execution.addItems([
            "OFF",
            "SIMULATION",
            "DEMO",
            "LIVE",
        ])

        execution_layout.addWidget(QLabel("Modo"), 0, 0)
        execution_layout.addWidget(self.cbo_execution, 0, 1)

        layout.addWidget(execution_box)
        execution_box.hide()

        profile_risk_notice = QLabel(
            "El modo de ejecución y la gestión de riesgo se definen por perfil en Perfiles. "
            "Cada perfil puede tener su propio modo, riesgo, límite diario y máximo de operaciones simultáneas."
        )
        profile_risk_notice.setWordWrap(True)
        profile_risk_notice.setObjectName("ProfileRiskNotice")
        set_visual_role(profile_risk_notice, "information")
        layout.addWidget(profile_risk_notice)

        # ==================================================
        # RIESGO
        # ==================================================

        risk_box = QGroupBox("Gestión de Riesgo")

        risk_layout = QGridLayout(risk_box)

        self.cbo_risk = QComboBox()

        self.cbo_risk.addItems([
            "PERCENT",
            "AMOUNT",
            "LOT",
        ])

        self.spn_percent = QDoubleSpinBox()

        self.spn_percent.setDecimals(2)

        self.spn_percent.setRange(0, 100)

        self.spn_percent.setSuffix(" %")

        self.spn_amount = QDoubleSpinBox()

        self.spn_amount.setMaximum(100000000)

        self.spn_amount.setPrefix("$ ")

        self.spn_lot = QDoubleSpinBox()

        self.spn_lot.setDecimals(2)

        self.spn_lot.setRange(0.01, 100)

        for row, (label, field) in enumerate((("Modo", self.cbo_risk), ("Porcentaje", self.spn_percent), ("Monto", self.spn_amount), ("Lote", self.spn_lot))):
            risk_layout.addWidget(QLabel(label), row, 0)
            risk_layout.addWidget(field, row, 1)
        risk_layout.setColumnStretch(1, 1)

        layout.addWidget(risk_box)
        risk_box.hide()

        # ==================================================
        # PROTECCIÓN
        # ==================================================

        protection_box = QGroupBox(
            "Protección"
        )

        protection = QGridLayout(
            protection_box
        )

        self.chk_break_even = QCheckBox()

        self.chk_trailing = QCheckBox()

        self.chk_partial = QCheckBox()

        self.chk_daily = QCheckBox()

        self.spn_drawdown = QDoubleSpinBox()

        self.spn_drawdown.setRange(
            0,
            100,
        )

        self.spn_drawdown.setSuffix("%")

        for row, (label, field) in enumerate((("Break Even", self.chk_break_even), ("Trailing Stop", self.chk_trailing), ("TP Parcial", self.chk_partial), ("Límite Diario", self.chk_daily), ("Drawdown Máximo", self.spn_drawdown))):
            protection.addWidget(QLabel(label), row, 0)
            protection.addWidget(field, row, 1)
        protection.setColumnStretch(1, 1)

        layout.addWidget(protection_box)
        protection_box.hide()

        # ==================================================
        # GENERAL
        # ==================================================

        general_box = QGroupBox(
            "General"
        )
        set_visual_role(general_box, "panel")

        general = QGridLayout(general_box)

        self.spn_interval = QSpinBox()

        self.spn_interval.setRange(
            1,
            60,
        )

        self.spn_interval.setSuffix(" s")

        self.chk_logs = QCheckBox()

        self.chk_sound = QCheckBox()

        for row, (label, field) in enumerate((("Intervalo Monitor", self.spn_interval), ("Guardar Logs", self.chk_logs), ("Sonidos", self.chk_sound))):
            general.addWidget(QLabel(label), row, 0)
            general.addWidget(field, row, 1)
        general.setColumnStretch(1, 1)

        layout.addWidget(general_box)

        # ==================================================
        # BOTONES
        # ==================================================

        buttons = QHBoxLayout()

        self.btn_save = QPushButton(
            "Guardar"
        )

        self.btn_reload = QPushButton(
            "Recargar"
        )

        buttons.addStretch()

        buttons.addWidget(
            self.btn_reload
        )

        buttons.addWidget(
            self.btn_save
        )

        layout.addLayout(buttons)

        self.btn_save.clicked.connect(
            self.save
        )

        self.btn_reload.clicked.connect(
            self.load
        )

    # ======================================================

    def load(self):

        self.cbo_risk.setCurrentText(
            settings_repository.get(
                "risk_mode",
                "PERCENT",
            )
        )

        self.spn_percent.setValue(
            settings_repository.get_float(
                "risk_percent",
                2.0,
            )
        )

        self.spn_amount.setValue(
            settings_repository.get_float(
                "risk_amount",
                100,
            )
        )

        self.spn_lot.setValue(
            settings_repository.get_float(
                "fixed_lot",
                0.10,
            )
        )

        self.chk_break_even.setChecked(
            settings_repository.get_bool(
                "break_even",
                True,
            )
        )

        self.chk_trailing.setChecked(
            settings_repository.get_bool(
                "trailing_stop",
                True,
            )
        )

        self.chk_partial.setChecked(
            settings_repository.get_bool(
                "partial_tp",
                True,
            )
        )

        self.chk_daily.setChecked(
            settings_repository.get_bool(
                "daily_limit",
                True,
            )
        )

        self.spn_drawdown.setValue(
            settings_repository.get_float(
                "max_drawdown",
                20,
            )
        )

        self.spn_interval.setValue(
            settings_repository.get_int(
                "monitor_interval",
                2,
            )
        )

        self.chk_logs.setChecked(
            settings_repository.get_bool(
                "save_logs",
                True,
            )
        )

        self.chk_sound.setChecked(
            settings_repository.get_bool(
                "sound",
                True,
            )
        )

    # ======================================================

    def save(self):

        settings_repository.set(
            "risk_mode",
            self.cbo_risk.currentText(),
        )

        settings_repository.set(
            "risk_percent",
            self.spn_percent.value(),
        )

        settings_repository.set(
            "risk_amount",
            self.spn_amount.value(),
        )

        settings_repository.set(
            "fixed_lot",
            self.spn_lot.value(),
        )

        settings_repository.set(
            "break_even",
            self.chk_break_even.isChecked(),
        )

        settings_repository.set(
            "trailing_stop",
            self.chk_trailing.isChecked(),
        )

        settings_repository.set(
            "partial_tp",
            self.chk_partial.isChecked(),
        )

        settings_repository.set(
            "daily_limit",
            self.chk_daily.isChecked(),
        )

        settings_repository.set(
            "max_drawdown",
            self.spn_drawdown.value(),
        )

        settings_repository.set(
            "monitor_interval",
            self.spn_interval.value(),
        )

        settings_repository.set(
            "save_logs",
            self.chk_logs.isChecked(),
        )

        settings_repository.set(
            "sound",
            self.chk_sound.isChecked(),
        )

        QMessageBox.information(
            self,
            "Configuración",
            "Configuración guardada correctamente.",
        )
