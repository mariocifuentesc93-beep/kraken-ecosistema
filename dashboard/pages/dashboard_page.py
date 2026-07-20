from datetime import datetime

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen
from PySide6.QtWidgets import (QComboBox, QGridLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget, QStyle, QFrame, QHeaderView, QSizePolicy)

from dashboard.styles import BORDER_COLOR, CARD_COLOR, ERROR_COLOR, INFO_COLOR, PRIMARY_COLOR, SECONDARY_TEXT, WARNING_COLOR
from dashboard.ui_theme import configure_active_tables
from dashboard.icons import colored_icon
from repositories.profile_repository import profile_repository
from repositories.signal_repository import signal_repository
from services.trading_analytics_service import trading_analytics_service


class CurvePanel(QWidget):
    def __init__(self): super().__init__(); self.points=[]; self.setMinimumHeight(205); self.setStyleSheet(f"background:{CARD_COLOR};border:1px solid {BORDER_COLOR};border-radius:9px;")
    def set_points(self, points): self.points=points; self.update()
    def paintEvent(self, event):
        painter=QPainter(self); painter.setRenderHint(QPainter.Antialiasing); painter.setPen(QColor("#EAF1F5")); painter.drawText(14,24,"Curva de balance")
        chart=self.rect().adjusted(42,44,-18,-28); painter.setPen(QPen(QColor("#2D3743"),1,Qt.DotLine))
        for step in range(5): painter.drawLine(chart.left(), chart.top()+step*chart.height()/4, chart.right(), chart.top()+step*chart.height()/4)
        if not self.points:
            painter.setPen(QColor("#9EACB8")); painter.drawText(chart,Qt.AlignCenter,"◉\n\nAún no hay operaciones disponibles\nInicie Paper Trading o Simulación para generar datos."); return
        values=[point[1] for point in self.points]; low=min(values); high=max(values); span=high-low or 1; painter.setPen(QPen(QColor(PRIMARY_COLOR),2)); previous=None
        for index,value in enumerate(values):
            x=chart.left()+index*chart.width()/max(1,len(values)-1); y=chart.bottom()-(value-low)/span*chart.height()
            if previous: painter.drawLine(previous[0],previous[1],int(x),int(y))
            previous=(int(x),int(y))

class KpiGlyph(QWidget):
    def __init__(self, kind, color):
        super().__init__(); self.kind=kind; self.color=QColor(color); self.setFixedSize(34,34); self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        names={"wallet":"wallet","chart":"chart-spline","calendar":"calendar-days","target":"target","scale":"scale","draw":"trending-down","brief":"briefcase-business","hour":"hourglass","gear":"settings","person":"user-round","capital":"circle-dollar-sign"}
        self.svg_icon=colored_icon(names.get(kind, "circle-check"), color)
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.setBrush(QColor(self.color.red(),self.color.green(),self.color.blue(),35)); p.setPen(QPen(QColor(self.color.red(),self.color.green(),self.color.blue(),90),1)); p.drawRoundedRect(self.rect().adjusted(1,1,-1,-1),8,8); r=self.rect().adjusted(9,9,-9,-9); self.svg_icon.paint(p,r); p.end(); return
        if self.kind=="wallet": p.drawRoundedRect(r,3,3); p.drawLine(r.left(),r.top()+5,r.right(),r.top()+5)
        elif self.kind=="chart": p.drawLine(r.left(),r.bottom(),r.left(),r.top()); p.drawLine(r.left(),r.bottom(),r.right(),r.bottom()); p.drawLine(r.left()+2,r.bottom()-3,r.center().x(),r.center().y()); p.drawLine(r.center().x(),r.center().y(),r.right(),r.top()+2)
        elif self.kind=="calendar": p.drawRect(r); p.drawLine(r.left(),r.top()+5,r.right(),r.top()+5); p.drawPoint(r.center())
        elif self.kind=="target": p.drawEllipse(r); p.drawEllipse(r.adjusted(4,4,-4,-4)); p.drawLine(r.center().x(),r.top()-2,r.center().x(),r.bottom()+2)
        elif self.kind=="scale": p.drawLine(r.center().x(),r.top(),r.center().x(),r.bottom()); p.drawLine(r.left(),r.top()+5,r.right(),r.top()+5); p.drawEllipse(r.left(),r.top()+5,6,6); p.drawEllipse(r.right()-6,r.top()+5,6,6)
        elif self.kind=="draw": p.drawLine(r.left(),r.top(),r.left(),r.bottom()); p.drawLine(r.left(),r.bottom(),r.right(),r.bottom()); p.drawLine(r.left()+2,r.top()+3,r.center().x(),r.bottom()-5); p.drawLine(r.center().x(),r.bottom()-5,r.right(),r.bottom()-2)
        elif self.kind=="brief": p.drawRoundedRect(r,3,3); p.drawLine(r.left(),r.center().y(),r.right(),r.center().y())
        elif self.kind=="hour": p.drawLine(r.left(),r.top(),r.right(),r.top()); p.drawLine(r.left(),r.bottom(),r.right(),r.bottom()); p.drawLine(r.left(),r.top(),r.right(),r.bottom()); p.drawLine(r.right(),r.top(),r.left(),r.bottom())
        elif self.kind=="person": p.drawEllipse(r.center().x()-4,r.top(),8,8); p.drawRoundedRect(r.left()+2,r.center().y(),r.width()-4,r.height()//2,4,4)
        elif self.kind=="capital": p.drawText(self.rect(),Qt.AlignCenter,"$")
        else: p.drawEllipse(r)


class KpiCard(QFrame):
    HEIGHT = 66
    ICON_SIZE = 34
    RADIUS = 8

    def __init__(self, icon, title, accent, detail):
        super().__init__()
        self.setObjectName("KpiCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedHeight(self.HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(
            f"QFrame#KpiCard{{background:rgba(10,25,37,225);border:1px solid {BORDER_COLOR};"
            f"border-top:2px solid {accent};border-radius:{self.RADIUS}px;}} "
            "QFrame#KpiCard QLabel{background:transparent;border:0;}"
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 7, 10, 7)
        row.setSpacing(8)
        glyph = KpiGlyph(icon, accent)
        body = QVBoxLayout()
        body.setSpacing(0)
        label = QLabel(title)
        label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        label.setStyleSheet("color:#F4F7FA;font-size:10px;font-weight:700;border:0;")
        self.value = QLabel("—")
        self.value.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.value.setStyleSheet("color:#FFFFFF;font-size:15px;font-weight:700;border:0;")
        self.detail = QLabel(detail)
        self.detail.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.detail.setStyleSheet(f"color:{SECONDARY_TEXT};font-size:9px;border:0;")
        body.addWidget(label)
        body.addWidget(self.value)
        body.addWidget(self.detail)
        row.addWidget(glyph)
        row.addLayout(body, 1)

    def set_value(self, value, detail=None):
        self.value.setText(str(value))
        if detail is not None:
            self.detail.setText(str(detail))


class DashboardPage(QWidget):
    navigate_requested=Signal(str); action_requested=Signal(str); notifications_requested=Signal()
    def __init__(self): super().__init__(); self.build_ui(); self.connect_events(); self.refresh()
    def connect_events(self):
        from core.event_bus import event_bus
        for event in (event_bus.dashboardRefreshRequested,event_bus.statisticsUpdated,event_bus.profitUpdated,event_bus.operationCreated,event_bus.operationOpened,event_bus.operationClosed,event_bus.profileFinished): event.connect(self.refresh)
    def build_ui(self):
        layout=QVBoxLayout(self); layout.setContentsMargins(12,8,12,10); layout.setSpacing(8)
        head=QHBoxLayout(); title=QLabel("Centro de control"); title.setStyleSheet("font-size:18px;font-weight:700;"); self.subtitle=QLabel(); self.subtitle.setStyleSheet(f"color:{SECONDARY_TEXT};font-size:11px;"); self.notifications_button=QPushButton("Notificaciones"); self.notifications_button.setObjectName("DashboardNotificationsButton"); self.notifications_button.setMinimumSize(120, 26); self.notifications_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred); self.notifications_button.setToolTip("Mostrar u ocultar notificaciones"); self.notifications_button.setStyleSheet("#DashboardNotificationsButton{background:rgba(24,15,39,220);color:#D56BFF;border:1px solid #7C3AAD;border-radius:9px;padding:4px 10px;font-size:10px;font-weight:700;} #DashboardNotificationsButton:hover{background:#32194B;color:#EDAFFF;border-color:#C65CFF;}"); self.notifications_button.clicked.connect(self.notifications_requested); head.addWidget(title); head.addWidget(self.subtitle); head.addStretch(); head.addWidget(self.notifications_button); layout.addLayout(head)
        self.subtitle.hide()
        self.profile_filter = QComboBox()
        self.profile_filter.setMinimumSize(120, 26)
        self.profile_filter.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.profile_filter.setToolTip("Seleccione un perfil o el consolidado de todos los perfiles.")
        self.profile_filter.setStyleSheet("QComboBox{background:rgba(24,15,39,220);color:#D56BFF;border:1px solid #7C3AAD;border-radius:9px;padding:3px 22px 3px 9px;font-size:10px;font-weight:700;} QComboBox:hover{background:#32194B;color:#EDAFFF;border-color:#C65CFF;} QComboBox::drop-down{border:0;width:19px;} QComboBox QAbstractItemView{background:#181027;color:#EAF1F5;border:1px solid #7C3AAD;selection-background-color:#32194B;}")
        self.profile_filter.currentIndexChanged.connect(self.refresh)
        head.insertWidget(3, self.profile_filter)
        self.cards=QGridLayout(); self.cards.setHorizontalSpacing(9); self.cards.setVerticalSpacing(9)
        specs=(("wallet","Balance",PRIMARY_COLOR,"Respecto al inicial"),("chart","Equity",INFO_COLOR,"Flotante: $0.00"),("calendar","P/L diario",INFO_COLOR,"Hoy"),("calendar","P/L mensual",PRIMARY_COLOR,"Este mes"),("target","Win rate",PRIMARY_COLOR,"Operaciones cerradas"),("scale","Profit factor",WARNING_COLOR,"Relación beneficio/riesgo"),("draw","Drawdown",ERROR_COLOR,"Máx. histórico"),("brief","Abiertas",WARNING_COLOR,"Posiciones abiertas"),("hour","Pendientes",WARNING_COLOR,"Órdenes pendientes"),("gear","Modo",INFO_COLOR,"Ejecución actual"),("person","Perfil",INFO_COLOR,"Perfil activo"),("capital","Capital","#B64CFF","Capital disponible"))
        self.kpis={}
        for column in range(4): self.cards.setColumnStretch(column, 1)
        for index,(icon,name,color,detail) in enumerate(specs): card=KpiCard(icon,name,color,detail); self.cards.addWidget(card,index//4,index%4); self.kpis[name]=card
        self.curve=CurvePanel()
        self.curve.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        tables=QHBoxLayout(); self.operations=self.table(["ID","Símbolo","Dirección","Entrada","Salida","P/L","Estado","Hora cierre"]); self.signals=self.table(["Hora","Símbolo","Dirección","Entrada","TP1","SL","Estado"])
        self.operations_panel=self.panel("Operaciones recientes",self.operations); self.signals_panel=self.panel("Señales recientes",self.signals)
        tables.addWidget(self.operations_panel,1); tables.addWidget(self.signals_panel,1)
        dashboard_grid = QGridLayout()
        dashboard_grid.setHorizontalSpacing(10)
        dashboard_grid.setVerticalSpacing(9)
        dashboard_grid.addLayout(self.cards, 0, 0)
        dashboard_grid.addWidget(self.curve, 1, 0)
        dashboard_grid.addLayout(tables, 2, 0, 1, 2)
        self.connectivity = self.connectivity_panel()
        self.connectivity.setFixedHeight(190)
        self.connectivity.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.quick_actions = self.quick_panel()
        self.quick_actions.setFixedHeight(166)
        self.quick_actions.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.side_column = QWidget()
        self.side_column.setFixedWidth(350)
        self.side_column.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        side = QVBoxLayout()
        side.setContentsMargins(0, 0, 0, 0)
        side.setSpacing(9)
        side.addWidget(self.connectivity)
        side.addWidget(self.quick_actions)
        side.addStretch(1)
        self.side_column.setLayout(side)
        dashboard_grid.addWidget(self.side_column, 0, 1, 2, 1)
        dashboard_grid.setColumnStretch(0, 1)
        dashboard_grid.setColumnStretch(1, 0)
        dashboard_grid.setRowStretch(0, 0)
        dashboard_grid.setRowStretch(1, 1)
        dashboard_grid.setRowStretch(2, 0)
        layout.addLayout(dashboard_grid, 1)
        configure_active_tables(self)
    def _legacy_connectivity_panel(self):
        box=QWidget(); box.setObjectName("DashboardPanel"); box.setStyleSheet(f"#DashboardPanel{{background:{CARD_COLOR};border:1px solid {BORDER_COLOR};border-radius:9px;}}"); layout=QVBoxLayout(box); layout.setContentsMargins(12,10,12,10); layout.addWidget(QLabel("Conectividad"))
        self.connection_text=QLabel(); self.connection_text.setWordWrap(True); self.connection_text.setStyleSheet(f"color:{SECONDARY_TEXT};border:0;"); layout.addWidget(self.connection_text); diag=QPushButton("Diagnóstico"); diag.clicked.connect(lambda:self.navigate_requested.emit("MT5")); layout.addWidget(diag); return box
    def _legacy_quick_panel(self):
        box=QWidget(); box.setObjectName("DashboardQuickPanel"); box.setStyleSheet(f"#DashboardQuickPanel{{background:{CARD_COLOR};border:1px solid {BORDER_COLOR};border-radius:9px;}}"); layout=QVBoxLayout(box); layout.setContentsMargins(12,10,12,10); layout.addWidget(QLabel("Acciones rápidas"))
        for title,action in (("▷ Simulación","SIMULATION"),("↗ Paper Trading","Paper Trading"),("▦ Calendario","Calendario de Trading"),("◔ Analíticas","Analíticas"),("⚙ Configuración","Configuración")):
            button=QPushButton(title); button.clicked.connect(lambda checked=False,a=action:self._quick(a)); layout.addWidget(button)
        return box
    def connectivity_panel(self):
        box = QFrame()
        box.setObjectName("DashboardPanel")
        box.setStyleSheet(f"#DashboardPanel{{background:{CARD_COLOR};border:1px solid {BORDER_COLOR};border-radius:7px;}} #DashboardPanel QLabel{{background:transparent;border:0;color:#EAF1F5;}}")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(10, 9, 10, 8)
        layout.setSpacing(4)
        heading = QLabel("Conectividad")
        heading.setStyleSheet("font-size:11px;font-weight:700;")
        layout.addWidget(heading)
        self.connection_rows = {}
        for service, status, page in (("MT5", "Conectado", "MT5"), ("Telegram", "Conectado", "Telegram"), ("SQLite", "Disponible", "Configuración")):
            row, status_label = self._connection_row(service, status, page)
            self.connection_rows[service] = status_label
            layout.addWidget(row)
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"background:{BORDER_COLOR};border:0;")
        layout.addWidget(separator)
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 1, 0, 0)
        self.connection_updated = QLabel(f"Última actualización:\n{datetime.now():%d/%m/%Y %I:%M:%S %p}")
        self.connection_updated.setStyleSheet(f"color:{SECONDARY_TEXT};font-size:9px;")
        refresh = QLabel("⟳")
        refresh.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        refresh.setStyleSheet("color:#DCE7EF;font-size:18px;font-weight:400;")
        footer.addWidget(self.connection_updated)
        footer.addStretch()
        footer.addWidget(refresh)
        layout.addLayout(footer)
        # Kept as a sink for the legacy refresh path; visual state lives above.
        self.connection_text = QLabel()
        return box

    def _connection_row(self, service, status, page):
        row = QWidget()
        row.setStyleSheet("background:transparent;border:0;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        icon = QLabel()
        icon.setMinimumWidth(13)
        icon.setPixmap(colored_icon("circle-check", "#00C853").pixmap(13, 13))
        name = QLabel(service)
        name.setMinimumWidth(52)
        name.setStyleSheet("font-size:10px;")
        dot = QLabel()
        dot.setMinimumSize(6, 6)
        dot.setMaximumSize(6, 6)
        dot.setStyleSheet("background:#20C55A;border:0;border-radius:3px;")
        status_label = QLabel(status)
        status_label.setStyleSheet("font-size:10px;")
        diagnostic = QPushButton("Diagnóstico")
        diagnostic.setMinimumSize(72, 22)
        diagnostic.setStyleSheet(f"QPushButton{{background:#101D27;color:#EAF1F5;border:1px solid {BORDER_COLOR};border-radius:4px;padding:2px 6px;font-size:10px;}} QPushButton:hover{{border-color:#00C853;background:#153026;}}")
        diagnostic.clicked.connect(lambda checked=False, target=page: self.navigate_requested.emit(target))
        layout.addWidget(icon)
        layout.addWidget(name)
        layout.addWidget(dot)
        layout.addWidget(status_label)
        layout.addStretch()
        layout.addWidget(diagnostic)
        return row, status_label

    def quick_panel(self):
        box = QFrame()
        box.setObjectName("DashboardQuickPanel")
        box.setStyleSheet(f"#DashboardQuickPanel{{background:{CARD_COLOR};border:1px solid {BORDER_COLOR};border-radius:7px;}} #DashboardQuickPanel QLabel{{background:transparent;border:0;color:#EAF1F5;}}")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(10, 9, 10, 9)
        layout.setSpacing(6)
        heading = QLabel("Acciones rápidas")
        heading.setStyleSheet("font-size:11px;font-weight:700;")
        layout.addWidget(heading)
        actions = QGridLayout()
        actions.setHorizontalSpacing(6)
        actions.setVerticalSpacing(6)
        actions.setContentsMargins(0, 0, 0, 0)
        for row, col, icon, title, action, color in ((0, 0, "play", "Simulación", "SIMULATION", "#00D47A"), (0, 1, "chart-spline", "Paper Trading", "Paper Trading", "#45A3FF"), (1, 0, "calendar-days", "Calendario", "Calendario de Trading", "#D279FF"), (1, 1, "chart-no-axes-combined", "Analíticas", "Analíticas", "#FF9E28")):
            actions.addWidget(self._quick_button(icon, title, action, color), row, col)
        actions_widget = QWidget()
        actions_widget.setLayout(actions)
        actions_widget.setMinimumHeight(78)
        actions_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(actions_widget, 0, Qt.AlignTop)
        layout.addWidget(self._quick_button("settings", "Configuración", "Configuración", "#DDE6EE"), 0, Qt.AlignTop)
        layout.addStretch(1)
        return box

    def _quick_button(self, icon, title, action, color):
        button = QPushButton(title)
        button.setIcon(colored_icon(icon, color))
        button.setIconSize(QSize(18, 18))
        button.setMinimumHeight(36)
        button.setStyleSheet(f"QPushButton{{background:#101D27;color:{color};border:1px solid {BORDER_COLOR};border-radius:5px;padding:5px 7px;font-size:10px;font-weight:700;text-align:center;}} QPushButton:hover{{background:#182C3A;border-color:{color};}}")
        button.clicked.connect(lambda checked=False, current=action: self._quick(current))
        return button

    @staticmethod
    def table(headers):
        table=QTableWidget(); table.setColumnCount(len(headers)); table.setHorizontalHeaderLabels(headers); table.setEditTriggers(QTableWidget.NoEditTriggers); table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        table.verticalHeader().setDefaultSectionSize(22); table.verticalHeader().setMinimumSectionSize(22); table.horizontalHeader().setFixedHeight(22); table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); table.setWordWrap(False)
        table.setStyleSheet("QTableWidget{font-size:9px;} QTableWidget::item{padding:1px 3px;font-size:9px;} QHeaderView::section{padding:1px 3px;font-size:8px;font-weight:600;}")
        return table
    @staticmethod
    def panel(title, widget):
        panel=QWidget(); panel.setObjectName("DashboardTablePanel"); panel.setFixedHeight(148); panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed); panel.setStyleSheet(f"#DashboardTablePanel{{background:{CARD_COLOR};border:1px solid {BORDER_COLOR};border-radius:8px;}}"); box=QVBoxLayout(panel); box.setContentsMargins(9,6,9,7); box.setSpacing(4); heading=QLabel(title); heading.setStyleSheet("font-size:10px;font-weight:700;border:0;background:transparent;"); box.addWidget(heading); box.addWidget(widget); return panel
    def _refresh_profile_filter(self, active):
        current = self.profile_filter.currentData()
        profiles = profile_repository.get_active_profiles()
        valid_ids = {profile.id for profile in profiles}
        self.profile_filter.blockSignals(True)
        self.profile_filter.clear()
        self.profile_filter.addItem("Todos los perfiles", None)
        for profile in profiles:
            self.profile_filter.addItem(profile.name, profile.id)
        selected = current if current in valid_ids else (active.id if active else None)
        index = self.profile_filter.findData(selected)
        self.profile_filter.setCurrentIndex(max(0, index))
        self.profile_filter.blockSignals(False)
    def _quick(self, action): self.action_requested.emit(action) if action=="SIMULATION" else self.navigate_requested.emit(action)
    def refresh(self,*args):
        active=profile_repository.get_active()
        self._refresh_profile_filter(active)
        profile_id=self.profile_filter.currentData()
        metrics=trading_analytics_service.metrics({"profile":profile_id} if profile_id else {})
        rows=metrics["rows"]; open_count=sum(r["status"]=="OPEN" for r in rows); pending=sum(r["status"] in ("PENDING","QUEUED") for r in rows)
        values={"Balance":(f"{metrics['net']:,.2f}","Respecto al inicial"),"Equity":(f"{metrics['net']:,.2f}","Flotante: $0.00"),"P/L diario":(f"{metrics['net']:,.2f}","Hoy"),"P/L mensual":(f"{metrics['net']:,.2f}","Este mes"),"Win rate":(f"{metrics['win_rate']}%",f"{len(rows)} operaciones"),"Profit factor":(metrics['profit_factor'],"—"),"Drawdown":(f"{metrics['maximum_drawdown']:,.2f}","Máx. histórico"),"Abiertas":(open_count,"Posiciones abiertas"),"Pendientes":(pending,"Órdenes pendientes"),"Modo":(getattr(active,'execution_mode','OFF'),"Ejecución actual"),"Perfil":(getattr(active,'name','Sin perfil activo'),"Perfil activo"),"Capital":(f"{metrics['net']:,.2f}","Capital disponible")}
        selected_profile = profile_repository.get_by_id(profile_id) if profile_id else None
        values["Modo"] = (
            getattr(selected_profile, "execution_mode", "MÚLTIPLE"),
            "Ejecución actual",
        )
        values["Perfil"] = (
            getattr(selected_profile, "name", "Todos los perfiles"),
            "Filtro activo",
        )
        for key,(value,detail) in values.items(): self.kpis[key].set_value(value,detail)
        self.subtitle.setText(f"Perfil activo: {active.name}" if active else "Configure un perfil para comenzar"); self.curve.set_points(metrics["curve"]); self.connection_text.setText(f"MT5   • Desconectado\nTelegram   • Desconectado\nSQLite   • Disponible\n\nActualizado: {datetime.now():%H:%M:%S}")
        operations=list(reversed(rows[-6:])); self.operations.setRowCount(len(operations))
        for row,op in enumerate(operations):
            values=(op.get("id",""),op.get("symbol",""),op.get("direction",""),op.get("entry",""),op.get("exit",""),f"{float(op.get('net') or 0):.2f}",op.get("status",""),op.get("closed_at",""))
            for col,value in enumerate(values): self.operations.setItem(row,col,QTableWidgetItem(str(value)))
        signals=signal_repository.get_all()
        signals=[signal for signal in signals if profile_id is None or signal.profile_id == profile_id][:6]
        self.signals.setRowCount(len(signals))
        for row,signal in enumerate(signals):
            parsed=signal.metadata.get("parsed_fields",{})
            values=(signal.received_at,signal.symbol,signal.direction,parsed.get("entry",""),parsed.get("tp1",""),parsed.get("stop_loss",""),signal.status)
            for col,value in enumerate(values): self.signals.setItem(row,col,QTableWidgetItem(str(value)))
