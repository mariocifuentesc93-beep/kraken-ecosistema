from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from dashboard.styles import BORDER_COLOR, CARD_COLOR, ERROR_COLOR, INFO_COLOR, PRIMARY_COLOR, SECONDARY_TEXT, WARNING_COLOR
from dashboard.ui_theme import configure_active_tables
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
            painter.setPen(QColor("#9EACB8")); painter.drawText(chart,Qt.AlignCenter,"◉\n\nNo operations available yet\nPaper Trading o Simulación pueden generar datos."); return
        values=[point[1] for point in self.points]; low=min(values); high=max(values); span=high-low or 1; painter.setPen(QPen(QColor(PRIMARY_COLOR),2)); previous=None
        for index,value in enumerate(values):
            x=chart.left()+index*chart.width()/max(1,len(values)-1); y=chart.bottom()-(value-low)/span*chart.height()
            if previous: painter.drawLine(previous[0],previous[1],int(x),int(y))
            previous=(int(x),int(y))


class KpiCard(QWidget):
    def __init__(self, icon, title, accent, detail):
        super().__init__(); self.setObjectName("KpiCard"); self.setMinimumHeight(74); self.setMaximumHeight(82); self.setStyleSheet(f"QWidget#KpiCard{{background:{CARD_COLOR};border:1px solid {BORDER_COLOR};border-top:2px solid {accent};border-radius:8px;}} QWidget{{background:transparent;border:0;}}")
        row=QHBoxLayout(self); row.setContentsMargins(15,13,15,12); row.setSpacing(12)
        glyph=QLabel(icon); glyph.setFixedSize(40,40); glyph.setAlignment(Qt.AlignCenter); glyph.setStyleSheet(f"background:{accent}22;color:{accent};border:0;border-radius:8px;font-size:21px;")
        body=QVBoxLayout(); body.setSpacing(1); label=QLabel(title); label.setStyleSheet("color:#F4F7FA;font-weight:700;border:0;"); self.value=QLabel("—"); self.value.setStyleSheet("color:#FFFFFF;font-size:18px;font-weight:700;border:0;"); self.detail=QLabel(detail); self.detail.setStyleSheet(f"color:{SECONDARY_TEXT};font-size:10px;border:0;")
        body.addWidget(label); body.addWidget(self.value); body.addWidget(self.detail); row.addWidget(glyph); row.addLayout(body,1)
    def set_value(self, value, detail=None): self.value.setText(str(value)); self.detail.setText(str(detail)) if detail is not None else None


class DashboardPage(QWidget):
    navigate_requested=Signal(str); action_requested=Signal(str)
    def __init__(self): super().__init__(); self.build_ui(); self.connect_events(); self.refresh()
    def connect_events(self):
        from core.event_bus import event_bus
        for event in (event_bus.dashboardRefreshRequested,event_bus.statisticsUpdated,event_bus.profitUpdated,event_bus.operationCreated,event_bus.operationOpened,event_bus.operationClosed,event_bus.profileFinished): event.connect(self.refresh)
    def build_ui(self):
        layout=QVBoxLayout(self); layout.setContentsMargins(12,8,12,10); layout.setSpacing(8)
        head=QHBoxLayout(); title=QLabel("Centro de control"); title.setStyleSheet("font-size:21px;font-weight:700;"); self.subtitle=QLabel(); self.subtitle.setStyleSheet(f"color:{SECONDARY_TEXT};"); head.addWidget(title); head.addWidget(self.subtitle); head.addStretch(); layout.addLayout(head)
        self.cards=QGridLayout(); self.cards.setHorizontalSpacing(9); self.cards.setVerticalSpacing(9); layout.addLayout(self.cards)
        specs=(("▣","Balance",PRIMARY_COLOR,"Respecto al inicial"),("▥","Equity",INFO_COLOR,"Flotante: $0.00"),("▦","P/L diario",PRIMARY_COLOR,"Hoy"),("▦","P/L mensual",PRIMARY_COLOR,"Este mes"),("◎","Win rate",PRIMARY_COLOR,"Operaciones cerradas"),("⚖","Profit factor",WARNING_COLOR,"Relación beneficio/riesgo"),("⌁","Drawdown",ERROR_COLOR,"Máx. histórico"),("▣","Abiertas",WARNING_COLOR,"Posiciones abiertas"),("⌛","Pendientes",WARNING_COLOR,"Órdenes pendientes"),("⚙","Modo",INFO_COLOR,"Ejecución actual"),("●","Perfil",INFO_COLOR,"Perfil activo"),("$","Capital",WARNING_COLOR,"Capital disponible"))
        self.kpis={}
        for index,(icon,name,color,detail) in enumerate(specs): card=KpiCard(icon,name,color,detail); self.cards.addWidget(card,index//4,index%4); self.kpis[name]=card
        middle=QHBoxLayout(); self.curve=CurvePanel(); middle.addWidget(self.curve,7); right=QVBoxLayout(); right.setSpacing(9); right.addWidget(self.connectivity_panel(),1); right.addWidget(self.quick_panel(),1); middle.addLayout(right,3); layout.addLayout(middle,3)
        tables=QHBoxLayout(); self.operations=self.table(["ID","Símbolo","Dirección","Entrada","Salida","P/L","Estado","Hora cierre"]); self.signals=self.table(["Hora","Símbolo","Dirección","Entrada","TP1","SL","Estado"]); tables.addWidget(self.panel("Operaciones recientes",self.operations),1); tables.addWidget(self.panel("Señales recientes",self.signals),1); layout.addLayout(tables,2)
        configure_active_tables(self)
    def connectivity_panel(self):
        box=QWidget(); box.setObjectName("DashboardPanel"); box.setStyleSheet(f"#DashboardPanel{{background:{CARD_COLOR};border:1px solid {BORDER_COLOR};border-radius:9px;}}"); layout=QVBoxLayout(box); layout.setContentsMargins(12,10,12,10); layout.addWidget(QLabel("Conectividad"))
        self.connection_text=QLabel(); self.connection_text.setWordWrap(True); self.connection_text.setStyleSheet(f"color:{SECONDARY_TEXT};border:0;"); layout.addWidget(self.connection_text); diag=QPushButton("Diagnóstico"); diag.clicked.connect(lambda:self.navigate_requested.emit("MT5")); layout.addWidget(diag); return box
    def quick_panel(self):
        box=QWidget(); box.setObjectName("DashboardQuickPanel"); box.setStyleSheet(f"#DashboardQuickPanel{{background:{CARD_COLOR};border:1px solid {BORDER_COLOR};border-radius:9px;}}"); layout=QVBoxLayout(box); layout.setContentsMargins(12,10,12,10); layout.addWidget(QLabel("Acciones rápidas"))
        for title,action in (("▷ Simulación","SIMULATION"),("↗ Paper Trading","Paper Trading"),("▦ Calendario","Calendario de Trading"),("◔ Analíticas","Analíticas"),("⚙ Configuración","Configuración")):
            button=QPushButton(title); button.clicked.connect(lambda checked=False,a=action:self._quick(a)); layout.addWidget(button)
        return box
    @staticmethod
    def table(headers):
        table=QTableWidget(); table.setColumnCount(len(headers)); table.setHorizontalHeaderLabels(headers); table.setEditTriggers(QTableWidget.NoEditTriggers); table.setMinimumHeight(125)
        table.verticalHeader().setDefaultSectionSize(21); table.horizontalHeader().setFixedHeight(25)
        table.setStyleSheet("QTableWidget::item{padding:2px 4px;font-size:10px;} QHeaderView::section{padding:3px 4px;font-size:10px;font-weight:600;}")
        return table
    @staticmethod
    def panel(title, widget):
        panel=QWidget(); panel.setObjectName("DashboardTablePanel"); panel.setStyleSheet(f"#DashboardTablePanel{{background:{CARD_COLOR};border:1px solid {BORDER_COLOR};border-radius:9px;}}"); box=QVBoxLayout(panel); box.setContentsMargins(10,8,10,8); heading=QLabel(title); heading.setStyleSheet("font-weight:700;border:0;background:transparent;"); box.addWidget(heading); box.addWidget(widget); return panel
    def _quick(self, action): self.action_requested.emit(action) if action=="SIMULATION" else self.navigate_requested.emit(action)
    def refresh(self,*args):
        active=profile_repository.get_active(); metrics=trading_analytics_service.metrics({"profile":active.id} if active else {}); rows=metrics["rows"]; open_count=sum(r["status"]=="OPEN" for r in rows); pending=sum(r["status"] in ("PENDING","QUEUED") for r in rows)
        values={"Balance":(f"{metrics['net']:,.2f}","Respecto al inicial"),"Equity":(f"{metrics['net']:,.2f}","Flotante: $0.00"),"P/L diario":(f"{metrics['net']:,.2f}","Hoy"),"P/L mensual":(f"{metrics['net']:,.2f}","Este mes"),"Win rate":(f"{metrics['win_rate']}%",f"{len(rows)} operaciones"),"Profit factor":(metrics['profit_factor'],"—"),"Drawdown":(f"{metrics['maximum_drawdown']:,.2f}","Máx. histórico"),"Abiertas":(open_count,"Posiciones abiertas"),"Pendientes":(pending,"Órdenes pendientes"),"Modo":(getattr(active,'execution_mode','OFF'),"Ejecución actual"),"Perfil":(getattr(active,'name','Sin perfil activo'),"Perfil activo"),"Capital":(f"{metrics['net']:,.2f}","Capital disponible")}
        for key,(value,detail) in values.items(): self.kpis[key].set_value(value,detail)
        self.subtitle.setText(f"Perfil activo: {active.name}" if active else "Configure un perfil para comenzar"); self.curve.set_points(metrics["curve"]); self.connection_text.setText(f"MT5   • Desconectado\nTelegram   • Desconectado\nSQLite   • Disponible\n\nActualizado: {datetime.now():%H:%M:%S}")
        operations=list(reversed(rows[-6:])); self.operations.setRowCount(len(operations))
        for row,op in enumerate(operations):
            values=(op.get("id",""),op.get("symbol",""),op.get("direction",""),op.get("entry",""),op.get("exit",""),f"{float(op.get('net') or 0):.2f}",op.get("status",""),op.get("closed_at",""))
            for col,value in enumerate(values): self.operations.setItem(row,col,QTableWidgetItem(str(value)))
        signals=signal_repository.get_all()[:6]; self.signals.setRowCount(len(signals))
        for row,signal in enumerate(signals):
            parsed=signal.metadata.get("parsed_fields",{})
            values=(signal.received_at,signal.symbol,signal.direction,parsed.get("entry",""),parsed.get("tp1",""),parsed.get("stop_loss",""),signal.status)
            for col,value in enumerate(values): self.signals.setItem(row,col,QTableWidgetItem(str(value)))
