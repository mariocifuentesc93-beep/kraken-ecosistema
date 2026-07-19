from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QDoubleSpinBox,
    QSpinBox,
    QCheckBox,
    QGroupBox,
)


class RiskTab(QWidget):

    def __init__(self):

        super().__init__()

        self.profile = None

        self.build_ui()

    # ---------------------------------------------------------

    def build_ui(self):

        main = QVBoxLayout(self)

        # =====================================================
        # RIESGO
        # =====================================================

        risk = QGroupBox("Gestión de Riesgo")

        grid = QGridLayout(risk)

        # -----------------------------------------------------

        self.risk_percent = QDoubleSpinBox()

        self.risk_percent.setDecimals(2)

        self.risk_percent.setSuffix(" %")

        self.risk_percent.setRange(0.01,100)

        self.risk_percent.setValue(1.00)

        # -----------------------------------------------------

        self.daily_loss = QDoubleSpinBox()

        self.daily_loss.setSuffix(" %")

        self.daily_loss.setRange(0,100)

        self.daily_loss.setValue(5)

        # -----------------------------------------------------

        self.weekly_loss = QDoubleSpinBox()

        self.weekly_loss.setSuffix(" %")

        self.weekly_loss.setRange(0,100)

        self.weekly_loss.setValue(10)

        # -----------------------------------------------------

        self.monthly_loss = QDoubleSpinBox()

        self.monthly_loss.setSuffix(" %")

        self.monthly_loss.setRange(0,100)

        self.monthly_loss.setValue(20)

        # -----------------------------------------------------

        self.max_positions = QSpinBox()

        self.max_positions.setRange(1,100)

        self.max_positions.setValue(5)

        # -----------------------------------------------------

        self.max_losses = QSpinBox()

        self.max_losses.setRange(1,20)

        self.max_losses.setValue(3)

        # -----------------------------------------------------

        self.max_lot = QDoubleSpinBox()

        self.max_lot.setDecimals(2)

        self.max_lot.setRange(0.01,1000)

        self.max_lot.setValue(5)

        # -----------------------------------------------------

        grid.addWidget(QLabel("Riesgo por operación"),0,0)

        grid.addWidget(self.risk_percent,0,1)

        grid.addWidget(QLabel("Pérdida diaria"),1,0)

        grid.addWidget(self.daily_loss,1,1)

        grid.addWidget(QLabel("Pérdida semanal"),2,0)

        grid.addWidget(self.weekly_loss,2,1)

        grid.addWidget(QLabel("Pérdida mensual"),3,0)

        grid.addWidget(self.monthly_loss,3,1)

        grid.addWidget(QLabel("Máx. operaciones"),4,0)

        grid.addWidget(self.max_positions,4,1)

        grid.addWidget(QLabel("Pérdidas consecutivas"),5,0)

        grid.addWidget(self.max_losses,5,1)

        grid.addWidget(QLabel("Lote máximo"),6,0)

        grid.addWidget(self.max_lot,6,1)

        main.addWidget(risk)

        # =====================================================
        # PROTECCIONES
        # =====================================================

        protection = QGroupBox("Protecciones")

        protection_layout = QVBoxLayout(protection)

        self.block_daily = QCheckBox(

            "Bloquear perfil al alcanzar pérdida diaria"

        )

        self.block_weekly = QCheckBox(

            "Bloquear perfil al alcanzar pérdida semanal"

        )

        self.block_monthly = QCheckBox(

            "Bloquear perfil al alcanzar pérdida mensual"

        )

        self.block_losses = QCheckBox(

            "Bloquear después de pérdidas consecutivas"

        )

        self.block_drawdown = QCheckBox(

            "Bloquear por Drawdown"

        )

        self.resume_next_day = QCheckBox(

            "Reactivar automáticamente al día siguiente"

        )

        self.resume_next_day.setChecked(True)

        protection_layout.addWidget(self.block_daily)

        protection_layout.addWidget(self.block_weekly)

        protection_layout.addWidget(self.block_monthly)

        protection_layout.addWidget(self.block_losses)

        protection_layout.addWidget(self.block_drawdown)

        protection_layout.addWidget(self.resume_next_day)

        main.addWidget(protection)

        main.addStretch()

    # ---------------------------------------------------------

    def load(self, profile):

        self.profile = profile

        if profile is None:

            return

        #
        # Próximamente:
        #
        # cargar configuración de riesgo
        #