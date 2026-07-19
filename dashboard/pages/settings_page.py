from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
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


class SettingsPage(QWidget):

    def __init__(self):

        super().__init__()

        self.build_ui()

        self.load()

    # ======================================================

    def build_ui(self):

        layout = QVBoxLayout(self)

        # ==================================================
        # EJECUCIÓN
        # ==================================================

        execution_box = QGroupBox("Modo de ejecución")

        execution_layout = QFormLayout(execution_box)

        self.cbo_execution = QComboBox()

        self.cbo_execution.addItems([
            "OFF",
            "SIMULATION",
            "DEMO",
            "LIVE",
        ])

        execution_layout.addRow(
            QLabel("Modo"),
            self.cbo_execution,
        )

        layout.addWidget(execution_box)

        # ==================================================
        # RIESGO
        # ==================================================

        risk_box = QGroupBox("Gestión de Riesgo")

        risk_layout = QFormLayout(risk_box)

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

        risk_layout.addRow(
            "Modo",
            self.cbo_risk,
        )

        risk_layout.addRow(
            "Porcentaje",
            self.spn_percent,
        )

        risk_layout.addRow(
            "Monto",
            self.spn_amount,
        )

        risk_layout.addRow(
            "Lote",
            self.spn_lot,
        )

        layout.addWidget(risk_box)

        # ==================================================
        # PROTECCIÓN
        # ==================================================

        protection_box = QGroupBox(
            "Protección"
        )

        protection = QFormLayout(
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

        protection.addRow(
            "Break Even",
            self.chk_break_even,
        )

        protection.addRow(
            "Trailing Stop",
            self.chk_trailing,
        )

        protection.addRow(
            "TP Parcial",
            self.chk_partial,
        )

        protection.addRow(
            "Límite Diario",
            self.chk_daily,
        )

        protection.addRow(
            "Drawdown Máximo",
            self.spn_drawdown,
        )

        layout.addWidget(protection_box)

        # ==================================================
        # GENERAL
        # ==================================================

        general_box = QGroupBox(
            "General"
        )

        general = QFormLayout(general_box)

        self.spn_interval = QSpinBox()

        self.spn_interval.setRange(
            1,
            60,
        )

        self.spn_interval.setSuffix(" s")

        self.chk_logs = QCheckBox()

        self.chk_sound = QCheckBox()

        general.addRow(
            "Intervalo Monitor",
            self.spn_interval,
        )

        general.addRow(
            "Guardar Logs",
            self.chk_logs,
        )

        general.addRow(
            "Sonidos",
            self.chk_sound,
        )

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

        self.cbo_execution.setCurrentText(
            settings_repository.get(
                "execution_mode",
                "OFF",
            )
        )

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
            "execution_mode",
            self.cbo_execution.currentText(),
        )

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