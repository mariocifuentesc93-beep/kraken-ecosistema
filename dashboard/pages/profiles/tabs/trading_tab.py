from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QGroupBox,
)


class TradingTab(QWidget):

    def __init__(self):

        super().__init__()

        self.profile = None

        self.build_ui()

    # ---------------------------------------------------------

    def build_ui(self):

        main = QVBoxLayout(self)

        # =====================================================
        # EJECUCIÓN
        # =====================================================

        execution = QGroupBox("Motor de Ejecución")

        grid = QGridLayout(execution)

        self.auto_execute = QCheckBox(

            "Ejecutar automáticamente"

        )

        self.confirm_execution = QCheckBox(

            "Solicitar confirmación"

        )

        self.allow_manual = QCheckBox(

            "Aceptar operaciones manuales"

        )

        self.copy_tp = QCheckBox(

            "Copiar Take Profit"

        )

        self.copy_sl = QCheckBox(

            "Copiar Stop Loss"

        )

        self.allow_multiple = QCheckBox(

            "Permitir múltiples operaciones"

        )

        grid.addWidget(self.auto_execute,0,0)

        grid.addWidget(self.confirm_execution,0,1)

        grid.addWidget(self.allow_manual,1,0)

        grid.addWidget(self.allow_multiple,1,1)

        grid.addWidget(self.copy_tp,2,0)

        grid.addWidget(self.copy_sl,2,1)

        main.addWidget(execution)

        # =====================================================
        # BREAK EVEN
        # =====================================================

        breakeven = QGroupBox("Break Even")

        grid = QGridLayout(breakeven)

        self.be_enabled = QCheckBox("Activar")

        self.be_trigger = QSpinBox()

        self.be_trigger.setSuffix(" puntos")

        self.be_trigger.setMaximum(10000)

        self.be_offset = QSpinBox()

        self.be_offset.setSuffix(" puntos")

        self.be_offset.setMaximum(10000)

        grid.addWidget(self.be_enabled,0,0)

        grid.addWidget(QLabel("Activar en"),1,0)

        grid.addWidget(self.be_trigger,1,1)

        grid.addWidget(QLabel("Offset"),2,0)

        grid.addWidget(self.be_offset,2,1)

        main.addWidget(breakeven)

        # =====================================================
        # TRAILING STOP
        # =====================================================

        trailing = QGroupBox("Trailing Stop")

        grid = QGridLayout(trailing)

        self.trailing_enabled = QCheckBox("Activar")

        self.trailing_start = QSpinBox()

        self.trailing_start.setMaximum(10000)

        self.trailing_start.setSuffix(" puntos")

        self.trailing_step = QSpinBox()

        self.trailing_step.setMaximum(10000)

        self.trailing_step.setSuffix(" puntos")

        grid.addWidget(self.trailing_enabled,0,0)

        grid.addWidget(QLabel("Comenzar"),1,0)

        grid.addWidget(self.trailing_start,1,1)

        grid.addWidget(QLabel("Paso"),2,0)

        grid.addWidget(self.trailing_step,2,1)

        main.addWidget(trailing)

        # =====================================================
        # CIERRES PARCIALES
        # =====================================================

        partial = QGroupBox("Cierres Parciales")

        grid = QGridLayout(partial)

        self.partial_enabled = QCheckBox("Activar")

        self.partial_percent = QSpinBox()

        self.partial_percent.setRange(1,100)

        self.partial_percent.setSuffix("%")

        self.partial_trigger = QSpinBox()

        self.partial_trigger.setMaximum(10000)

        self.partial_trigger.setSuffix(" puntos")

        grid.addWidget(self.partial_enabled,0,0)

        grid.addWidget(QLabel("% a cerrar"),1,0)

        grid.addWidget(self.partial_percent,1,1)

        grid.addWidget(QLabel("Activar en"),2,0)

        grid.addWidget(self.partial_trigger,2,1)

        main.addWidget(partial)

        # =====================================================
        # IA
        # =====================================================

        ai = QGroupBox("Asistente IA")

        grid = QGridLayout(ai)

        self.ai_enabled = QCheckBox(

            "Usar IA"

        )

        self.ai_confirmation = QCheckBox(

            "Confirmar señal con IA"

        )

        self.ai_filter = QComboBox()

        self.ai_filter.addItems([

            "Desactivado",

            "Conservador",

            "Normal",

            "Agresivo"

        ])

        grid.addWidget(self.ai_enabled,0,0)

        grid.addWidget(self.ai_confirmation,1,0)

        grid.addWidget(QLabel("Filtro"),2,0)

        grid.addWidget(self.ai_filter,2,1)

        main.addWidget(ai)

        main.addStretch()

    # ---------------------------------------------------------

    def load(self, profile):

        self.profile = profile

        if profile is None:

            return

        #
        # Próximamente:
        #
        # Cargar configuración de trading
        #