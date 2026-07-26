from __future__ import annotations

from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from services.operational_alert_service import OperationalAlertService
from services.operational_health_service import OperationalHealthService
from services.operational_metrics_service import OperationalMetricsService
from services.signal_trace_service import SignalTraceService


class MonitoringSnapshotWorker(QObject):
    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, options):
        super().__init__()
        self.options = dict(options)

    @Slot()
    def run(self):
        try:
            health = OperationalHealthService().snapshot()
            trace_service = SignalTraceService()
            signal_id = self.options.get("signal_id")
            snapshot = {
                "health": health,
                "alerts": OperationalAlertService().derive(health),
                "decisions": trace_service.decisions(
                    limit=self.options["page_size"],
                    offset=self.options["offset"],
                    source=self.options.get("source"),
                    result=self.options.get("result"),
                ),
                "activity": trace_service.recent_activity(
                    limit=self.options["activity_limit"],
                    level=self.options.get("level"),
                    component=self.options.get("component"),
                    signal_id=self.options.get("activity_signal_id"),
                ),
                "metrics": OperationalMetricsService().calculate(
                    self.options["period"]
                ),
                "trace": trace_service.trace(signal_id) if signal_id else None,
            }
            self.completed.emit(snapshot)
        except Exception as error:
            self.failed.emit(str(error))
        finally:
            try:
                from database.database_manager import database_manager

                database_manager.close()
            finally:
                self.finished.emit()


class HealthCard(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("monitoringHealthCard")
        layout = QVBoxLayout(self)
        self.title = QLabel(title)
        self.title.setProperty("role", "cardTitle")
        self.state = QLabel("—")
        self.state.setProperty("role", "status")
        self.detail = QLabel("Sin datos")
        self.detail.setWordWrap(True)
        self.updated = QLabel("—")
        self.updated.setProperty("role", "subtitle")
        layout.addWidget(self.title)
        layout.addWidget(self.state)
        layout.addWidget(self.detail)
        layout.addWidget(self.updated)

    def update_value(self, card):
        state = str(card.get("state", "—"))
        self.state.setText(state)
        self.state.setProperty("status", state)
        self.state.style().unpolish(self.state)
        self.state.style().polish(self.state)
        self.detail.setText(str(card.get("detail") or "Sin detalle"))
        self.updated.setText(f"Actualizado: {card.get('updated_at') or '—'}")


class OperationalMonitoringPage(QWidget):
    """Read-only operational overview.  No trading action is exposed."""

    openTerminalsRequested = Signal()
    CARD_NAMES = (
        "Kraken Runtime", "INTERNAL", "Telegram", "SQLite", "Scanner",
        "Routing", "Risk Engine", "Execution Preflight",
    )

    def __init__(self, parent=None, auto_refresh=True):
        super().__init__(parent)
        self._thread = None
        self._worker = None
        self._snapshot = {}
        self._selected_signal_id = None
        self._page = 0
        self._auto_refresh = bool(auto_refresh)
        self._build_ui()
        self._connect_events()
        self.timer = QTimer(self)
        self.timer.setInterval(5000)
        self.timer.timeout.connect(self.refresh)

    def _build_ui(self):
        root = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.status = QLabel("Esperando actualización…")
        self.refresh_button = QPushButton("Actualizar")
        self.terminals_button = QPushButton("Abrir en Terminales MT5")
        self.interval = QSpinBox()
        self.interval.setRange(3, 60)
        self.interval.setValue(5)
        self.interval.setSuffix(" s")
        toolbar.addWidget(self.status)
        toolbar.addStretch()
        toolbar.addWidget(QLabel("Refresco"))
        toolbar.addWidget(self.interval)
        toolbar.addWidget(self.terminals_button)
        toolbar.addWidget(self.refresh_button)
        root.addLayout(toolbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        cards_layout = QGridLayout()
        self.cards = {}
        for index, title in enumerate(self.CARD_NAMES):
            card = HealthCard(title)
            self.cards[title] = card
            cards_layout.addWidget(card, index // 4, index % 4)
        content_layout.addLayout(cards_layout)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_pipeline_tab(), "Pipeline en vivo")
        self.tabs.addTab(self._build_decisions_tab(), "Decisiones")
        self.tabs.addTab(self._build_health_tab(), "Terminales y perfiles")
        self.tabs.addTab(self._build_activity_tab(), "Actividad")
        self.tabs.addTab(self._build_alerts_tab(), "Alertas")
        self.tabs.addTab(self._build_metrics_tab(), "Métricas")
        content_layout.addWidget(self.tabs)
        scroll.setWidget(content)
        root.addWidget(scroll)

    def _build_pipeline_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.pipeline_title = QLabel("Seleccione una señal en Decisiones.")
        self.pipeline_table = self._table(
            ("Etapa", "Estado", "Inicio", "Fin", "Duración", "Detalle", "Motivo", "Referencia")
        )
        self.pipeline_details = QPlainTextEdit()
        self.pipeline_details.setReadOnly(True)
        self.pipeline_details.setMaximumHeight(130)
        layout.addWidget(self.pipeline_title)
        layout.addWidget(self.pipeline_table)
        layout.addWidget(self.pipeline_details)
        return page

    def _build_decisions_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        filters = QHBoxLayout()
        self.source_filter = QComboBox()
        self.source_filter.addItems(("Todas", "INTERNAL", "TELEGRAM"))
        self.result_filter = QComboBox()
        self.result_filter.addItems((
            "Todos", "PERSISTED", "PUBLISHED", "NO_ELIGIBLE_PROFILES",
            "SIMULATED", "RISK_REJECTED", "PREFLIGHT_BLOCKED", "SENT",
            "FILLED", "FAILED",
        ))
        self.page_size = QComboBox()
        self.page_size.addItems(("25", "50", "100"))
        self.previous_button = QPushButton("Anterior")
        self.next_button = QPushButton("Siguiente")
        self.page_label = QLabel("Página 1")
        filters.addWidget(QLabel("Fuente"))
        filters.addWidget(self.source_filter)
        filters.addWidget(QLabel("Resultado"))
        filters.addWidget(self.result_filter)
        filters.addWidget(QLabel("Filas"))
        filters.addWidget(self.page_size)
        filters.addStretch()
        filters.addWidget(self.previous_button)
        filters.addWidget(self.page_label)
        filters.addWidget(self.next_button)
        self.decisions_table = self._table(
            ("Signal ID", "Fecha", "Fuente", "Símbolo", "Perfil", "Resultado",
             "Motivo", "Telegram", "Operación", "Duración")
        )
        layout.addLayout(filters)
        layout.addWidget(self.decisions_table)
        return page

    def _build_health_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Terminales MT5 (resumen de solo lectura)"))
        self.terminals_table = self._table(
            ("Terminal", "Proceso", "Activa", "Trading", "Scanner", "Cuenta esperada",
             "Cuenta detectada", "Coincidencia", "Conexión", "Scanner status", "Diagnóstico")
        )
        layout.addWidget(self.terminals_table)
        layout.addWidget(QLabel("Elegibilidad de perfiles INTERNAL"))
        self.profiles_table = self._table(
            ("Perfil", "Activo", "Fuente", "Modo", "Cuenta", "Terminal",
             "Catálogo", "Símbolos", "Elegible", "Motivo")
        )
        layout.addWidget(self.profiles_table)
        return page

    def _build_activity_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        filters = QHBoxLayout()
        self.level_filter = QComboBox()
        self.level_filter.addItems(("Todos", "INFO", "WARNING", "ERROR", "CRITICAL"))
        self.component_filter = QComboBox()
        self.component_filter.addItems((
            "Todos", "Internal", "Telegram", "Routing", "Risk",
            "ExecutionPreflight", "MT5",
        ))
        self.activity_signal_filter = QSpinBox()
        self.activity_signal_filter.setRange(0, 999999999)
        self.activity_signal_filter.setSpecialValueText("Todos")
        filters.addWidget(QLabel("Nivel"))
        filters.addWidget(self.level_filter)
        filters.addWidget(QLabel("Componente"))
        filters.addWidget(self.component_filter)
        filters.addWidget(QLabel("Signal ID"))
        filters.addWidget(self.activity_signal_filter)
        filters.addStretch()
        self.activity_table = self._table(
            ("Hora", "Nivel", "Componente", "Evento")
        )
        layout.addLayout(filters)
        layout.addWidget(self.activity_table)
        return page

    def _build_alerts_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.alerts_table = self._table(
            ("Severidad", "Estado", "Componente", "Alerta", "Mensaje",
             "Primera", "Última", "Ocurrencias", "Acción recomendada")
        )
        layout.addWidget(self.alerts_table)
        return page

    def _build_metrics_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        row = QHBoxLayout()
        self.period_filter = QComboBox()
        self.period_filter.addItem("Sesión actual", "SESSION")
        self.period_filter.addItem("Hoy", "TODAY")
        self.period_filter.addItem("Últimos 7 días", "7D")
        self.period_filter.addItem("Últimos 30 días", "30D")
        row.addWidget(QLabel("Periodo"))
        row.addWidget(self.period_filter)
        row.addStretch()
        self.metrics_table = self._table(("Métrica", "Valor"))
        layout.addLayout(row)
        layout.addWidget(self.metrics_table)
        return page

    @staticmethod
    def _table(headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        return table

    def _connect_events(self):
        self.refresh_button.clicked.connect(self.refresh)
        self.terminals_button.clicked.connect(self.openTerminalsRequested)
        self.interval.valueChanged.connect(
            lambda value: self.timer.setInterval(value * 1000)
        )
        self.decisions_table.itemSelectionChanged.connect(self._decision_selected)
        self.previous_button.clicked.connect(self._previous_page)
        self.next_button.clicked.connect(self._next_page)
        for widget in (
            self.source_filter, self.result_filter, self.page_size,
            self.level_filter, self.component_filter, self.period_filter,
        ):
            widget.currentIndexChanged.connect(self._filters_changed)
        self.activity_signal_filter.valueChanged.connect(self._filters_changed)

    def refresh(self, *_args):
        if self._thread is not None and self._thread.isRunning():
            return
        self.refresh_button.setEnabled(False)
        self.status.setText("Actualizando en segundo plano…")
        options = {
            "page_size": int(self.page_size.currentText()),
            "offset": self._page * int(self.page_size.currentText()),
            "source": self._filter_value(self.source_filter),
            "result": self._filter_value(self.result_filter),
            "level": self._filter_value(self.level_filter),
            "component": self._filter_value(self.component_filter),
            "activity_signal_id": self.activity_signal_filter.value() or None,
            "activity_limit": 100,
            "period": self.period_filter.currentData(),
            "signal_id": self._selected_signal_id,
        }
        self._thread = QThread(self)
        self._worker = MonitoringSnapshotWorker(options)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.completed.connect(self._apply_snapshot)
        self._worker.failed.connect(self._refresh_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._worker_finished)
        self._thread.start()

    @Slot(object)
    def _apply_snapshot(self, snapshot):
        self._snapshot = snapshot
        health = snapshot["health"]
        for title, card in self.cards.items():
            card.update_value(health["cards"].get(title, {}))
        self._fill_terminals(health["terminals"])
        self._fill_profiles(health["profiles"])
        self._fill_decisions(snapshot["decisions"])
        self._fill_activity(snapshot["activity"])
        self._fill_alerts(snapshot["alerts"])
        self._fill_metrics(snapshot["metrics"])
        self._fill_trace(snapshot.get("trace"))
        self.status.setText(f"Actualizado: {health['updated_at']}")

    @Slot(str)
    def _refresh_failed(self, message):
        self.status.setText(f"Monitoreo no disponible: {message}")

    @Slot()
    def _worker_finished(self):
        self.refresh_button.setEnabled(True)
        self._thread = None
        self._worker = None

    def _fill_terminals(self, rows):
        values = [
            (
                row["name"], row["process_status"], self._yes(row["active"]),
                self._yes(row["can_trade"]), self._yes(row["can_scan"]),
                row["expected_login"] or "—", row["detected_login"] or "—",
                row["account_match_status"], row["trading_connection_status"],
                row["scanner_status"], row["last_seen_at"] or "—",
            ) for row in rows
        ]
        self._fill(self.terminals_table, values)

    def _fill_profiles(self, rows):
        self._fill(self.profiles_table, [
            (
                row["name"], self._yes(row["active"] and row["enabled"]),
                row["signal_source_mode"], row["execution_mode"],
                row["account_name"] or "—", row["terminal_name"] or "—",
                row["catalog_id"], row["enabled_symbols"],
                self._yes(row["eligible"]), row["eligibility_reason"],
            ) for row in rows
        ])

    def _fill_decisions(self, rows):
        self._decision_ids = []
        values = []
        for row in rows:
            self._decision_ids.append(row["id"])
            values.append((
                row["id"], row["received_at"] or row["created_at"], row["source"],
                row["symbol"], row["profile"] or "—", row["result"],
                row["rejection_reason"] or "—", row["telegram_status"] or "—",
                row["operation_status"] or "—", row["duration_ms"] or "—",
            ))
        self._fill(self.decisions_table, values)
        self.page_label.setText(f"Página {self._page + 1}")
        self.previous_button.setEnabled(self._page > 0)
        self.next_button.setEnabled(len(rows) == int(self.page_size.currentText()))

    def _fill_activity(self, rows):
        self._fill(self.activity_table, [
            (row["created_at"], row["level"], row["module"], row["message"])
            for row in rows
        ])

    def _fill_alerts(self, rows):
        self._fill(self.alerts_table, [
            (
                row["severity"], row["state"], row["component"], row["alert_type"],
                row["message"], row["first_seen_at"], row["last_seen_at"],
                row["occurrence_count"], row["recommended_action"],
            ) for row in rows
        ])

    def _fill_metrics(self, metrics):
        labels = {
            "signals_detected": "Señales detectadas",
            "signals_persisted": "Señales persistidas",
            "telegram_publications": "Publicaciones Telegram",
            "simulations": "Simulaciones",
            "risk_rejections": "Rechazos de riesgo",
            "preflight_blocks": "Bloqueos pre-flight",
            "orders_sent": "Órdenes enviadas",
            "orders_filled": "Órdenes llenadas",
            "failures": "Fallos",
            "duplicates_blocked": "Duplicados bloqueados",
            "average_processing_ms": "Tiempo medio (ms)",
        }
        self._fill(self.metrics_table, [
            (label, metrics.get(key, 0)) for key, label in labels.items()
        ])

    def _fill_trace(self, trace):
        if not trace:
            self.pipeline_table.setRowCount(0)
            self.pipeline_title.setText("Seleccione una señal en Decisiones.")
            self.pipeline_details.clear()
            return
        signal = trace["signal"]
        self.pipeline_title.setText(
            f"Signal ID {signal['id']} · {signal['source']} · {signal['symbol']}"
        )
        self._fill(self.pipeline_table, [
            (
                row["stage"], row["status"], row["started_at"], row["finished_at"],
                row["duration_ms"] if row["duration_ms"] is not None else "—",
                row["detail"], row["reason"], row["reference"],
            ) for row in trace["stages"]
        ])
        self.pipeline_details.setPlainText(
            f"External ID: {signal.get('external_signal_id') or '—'}\n"
            f"Idempotencia: {signal.get('idempotency_key') or '—'}\n"
            f"Publicaciones: {len(trace['publications'])} · "
            f"Operaciones: {len(trace['operations'])} · "
            f"Eventos correlacionados: {len(trace['events'])}"
        )

    @staticmethod
    def _fill(table, rows):
        table.setSortingEnabled(False)
        table.setRowCount(len(rows))
        for row_index, values in enumerate(rows):
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value if value is not None else "—"))
                item.setData(Qt.UserRole, value)
                table.setItem(row_index, column, item)
        table.resizeColumnsToContents()

    @staticmethod
    def _yes(value):
        return "Sí" if value else "No"

    @staticmethod
    def _filter_value(combo):
        value = combo.currentText()
        return None if value in {"Todas", "Todos"} else value

    def _decision_selected(self):
        row = self.decisions_table.currentRow()
        if row < 0 or row >= len(getattr(self, "_decision_ids", [])):
            return
        signal_id = self._decision_ids[row]
        if signal_id != self._selected_signal_id:
            self._selected_signal_id = signal_id
            self.tabs.setCurrentIndex(0)
            self.refresh()

    def _filters_changed(self, *_args):
        self._page = 0
        self.refresh()

    def _previous_page(self):
        self._page = max(0, self._page - 1)
        self.refresh()

    def _next_page(self):
        self._page += 1
        self.refresh()

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if self._auto_refresh:
            if not self.timer.isActive():
                self.timer.start()
            QTimer.singleShot(0, self.refresh)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)
