from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from dashboard.ui_theme import NEGATIVE, POSITIVE, WARNING, dashboard_card
from repositories.profile_repository import profile_repository
from repositories.signal_repository import signal_repository
from services.trading_analytics_service import trading_analytics_service


class MiniCurve(QWidget):
    def __init__(self): super().__init__(); self.points=[]; self.setMinimumHeight(150)
    def set_points(self,points): self.points=points; self.update()
    def paintEvent(self,event):
        painter=QPainter(self); painter.fillRect(self.rect(),QColor("#2E3440")); painter.setPen(QColor("#B0BEC5")); painter.drawText(12,20,"Curva de balance")
        if not self.points: painter.drawText(12,48,"Sin operaciones cerradas todavía"); return
        values=[point[1] for point in self.points]; low=min(values); high=max(values); span=high-low or 1; last=None; painter.setPen(QColor(POSITIVE))
        for index,value in enumerate(values):
            x=12+index*(self.width()-24)/max(1,len(values)-1); y=self.height()-18-(value-low)/span*(self.height()-50)
            if last:painter.drawLine(last[0],last[1],int(x),int(y))
            last=(int(x),int(y))


class DashboardPage(QWidget):
    navigate_requested=Signal(str)
    action_requested=Signal(str)
    def __init__(self): super().__init__(); self.build_ui(); self.connect_events(); self.refresh()
    def connect_events(self):
        from core.event_bus import event_bus
        for event in (event_bus.dashboardRefreshRequested,event_bus.statisticsUpdated,event_bus.profitUpdated,event_bus.operationCreated,event_bus.operationOpened,event_bus.operationClosed,event_bus.profileFinished): event.connect(self.refresh)
    def build_ui(self):
        layout=QVBoxLayout(self); layout.setContentsMargins(14,14,14,14); layout.setSpacing(10); title=QHBoxLayout(); heading=QLabel("Centro de control"); heading.setStyleSheet("font-size:22px;font-weight:700;"); self.subtitle=QLabel("Resumen operativo y conectividad"); title.addWidget(heading); title.addWidget(self.subtitle); title.addStretch(); layout.addLayout(title)
        self.cards=QGridLayout(); self.cards.setSpacing(8); layout.addLayout(self.cards)
        self.card_labels={}; metrics=(("Balance",POSITIVE),("Equity",POSITIVE),("P/L diario",POSITIVE),("P/L mensual",POSITIVE),("Win rate",POSITIVE),("Profit factor",WARNING),("Drawdown",NEGATIVE),("Abiertas",WARNING),("Pendientes",WARNING),("Modo",WARNING),("Perfil",POSITIVE))
        for index,(name,color) in enumerate(metrics):
            card=QWidget(); card.setStyleSheet(dashboard_card(color)); box=QVBoxLayout(card); label=QLabel(name); label.setStyleSheet("color:#B0BEC5;font-size:11px;"); value=QLabel("—"); value.setStyleSheet("font-size:20px;font-weight:700;"); box.addWidget(label); box.addWidget(value); self.cards.addWidget(card,index//4,index%4); self.card_labels[name]=value
        middle=QHBoxLayout(); self.curve=MiniCurve(); middle.addWidget(self.curve,2); self.connections=QLabel(); self.connections.setAlignment(Qt.AlignTop); self.connections.setStyleSheet(dashboard_card(WARNING)+"padding:12px;"); middle.addWidget(self.connections,1); layout.addLayout(middle,2)
        bottom=QHBoxLayout(); self.operations=self.table(["Hora","Símbolo","Lado","Neto","Estado"]); self.signals=self.table(["Hora","Símbolo","Lado","Estado"]); bottom.addWidget(self.panel("Operaciones recientes",self.operations),1); bottom.addWidget(self.panel("Señales recientes",self.signals),1); layout.addLayout(bottom,2)
        quick=QHBoxLayout(); quick.addWidget(QLabel("Acciones rápidas"));
        for name,action in (("Simulación","SIMULATION"),("Paper Trading","Paper Trading"),("Calendario","Calendario de Trading"),("Analíticas","Analíticas"),("Configuración","Configuración")):
            button=QPushButton(name); button.clicked.connect(lambda checked=False,a=action:self._quick(a)); quick.addWidget(button)
        quick.addStretch(); layout.addLayout(quick)
    @staticmethod
    def table(headers):
        table=QTableWidget(); table.setColumnCount(len(headers)); table.setHorizontalHeaderLabels(headers); table.setEditTriggers(QTableWidget.NoEditTriggers); table.setMaximumHeight(180); return table
    @staticmethod
    def panel(title,widget):
        panel=QWidget(); panel.setStyleSheet(dashboard_card()); box=QVBoxLayout(panel); label=QLabel(title); label.setStyleSheet("font-weight:700;"); box.addWidget(label); box.addWidget(widget); return panel
    def _quick(self,action):
        if action=="SIMULATION":self.action_requested.emit(action)
        else:self.navigate_requested.emit(action)
    def refresh(self,*args):
        active=profile_repository.get_active(); filters={"profile":active.id} if active else {}; metrics=trading_analytics_service.metrics(filters); rows=metrics["rows"]; open_count=sum(r["status"]=="OPEN" for r in rows); pending=sum(r["status"] in ("PENDING","QUEUED") for r in rows)
        values={"Balance":f"{metrics['net']:,.2f}","Equity":f"{metrics['net']:,.2f}","P/L diario":f"{metrics['net']:,.2f}","P/L mensual":f"{metrics['net']:,.2f}","Win rate":f"{metrics['win_rate']}%","Profit factor":metrics['profit_factor'],"Drawdown":f"{metrics['maximum_drawdown']:,.2f}","Abiertas":open_count,"Pendientes":pending,"Modo":getattr(active,'execution_mode','OFF'),"Perfil":getattr(active,'name','Sin perfil activo')}
        for name,value in values.items():self.card_labels[name].setText(str(value))
        self.subtitle.setText("Perfil activo" if active else "Configure un perfil para comenzar"); self.curve.set_points(metrics["curve"]); self.connections.setText("Conectividad\n\nMT5: pendiente de diagnóstico\nTelegram: pendiente de diagnóstico\nBase SQLite: disponible\n\nLos estados reales se actualizan desde la barra superior.")
        operations=list(reversed(rows[-6:])); self.operations.setRowCount(len(operations))
        for row,op in enumerate(operations):
            for col,value in enumerate((op.get("opened_at"),op.get("symbol"),op.get("direction"),f"{float(op.get('net') or 0):.2f}",op.get("status"))):self.operations.setItem(row,col,QTableWidgetItem(str(value)))
        signals=signal_repository.get_all()[:6]; self.signals.setRowCount(len(signals))
        for row,signal in enumerate(signals):
            for col,value in enumerate((signal.received_at,signal.symbol,signal.direction,signal.status)):self.signals.setItem(row,col,QTableWidgetItem(str(value)))
