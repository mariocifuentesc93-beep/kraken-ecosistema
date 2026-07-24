from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QComboBox, QDateEdit, QGridLayout, QHBoxLayout, QLabel,
                               QPushButton, QScrollArea, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget, QFileDialog)

from dashboard.styles import CARD_COLOR, ERROR_COLOR, SUCCESS_COLOR
from dashboard.ui_theme import set_visual_role
from repositories.profile_repository import profile_repository
from services.trading_analytics_service import trading_analytics_service


class ChartWidget(QWidget):
    def __init__(self,title): super().__init__(); self.title=title; self.values={}; self.setMinimumHeight(150)
    def set_values(self,values): self.values=values; self.update()
    def paintEvent(self,event):
        painter=QPainter(self); painter.fillRect(self.rect(),QColor(CARD_COLOR)); painter.setPen(QColor("#FFFFFF")); painter.drawText(10,20,self.title)
        if not self.values: painter.drawText(10,45,"Sin datos"); return
        data=list(self.values.values()); maximum=max(max(data),abs(min(data)),1); width=max(1,(self.width()-20)/len(data)); baseline=self.height()*0.62
        for index,(label,value) in enumerate(self.values.items()):
            height=abs(value)/maximum*(self.height()*0.42); x=10+index*width; color=QColor(SUCCESS_COLOR if value>=0 else ERROR_COLOR); painter.fillRect(int(x),int(baseline-height if value>=0 else baseline),max(2,int(width-3)),int(height),color)
        painter.setPen(QPen(QColor("#B0BEC5"),1)); painter.drawLine(5,int(baseline),self.width()-5,int(baseline))


class AnalyticsPage(QWidget):
    def __init__(self): super().__init__(); self.build_ui(); self.refresh()
    def build_ui(self):
        layout=QVBoxLayout(self); filters=QHBoxLayout(); self.start=QDateEdit(); self.end=QDateEdit(); self.start.setDate(date(date.today().year,1,1)); self.end.setDate(date.today()); self.profile=QComboBox(); self.symbol=QComboBox(); self.account=QComboBox(); self.mode=QComboBox(); self.source=QComboBox()
        for label,field,items in (("Desde",self.start,None),("Hasta",self.end,None),("Perfil",self.profile,["All"]),("Símbolo",self.symbol,["All"]),("Cuenta",self.account,["All"]),("Modo",self.mode,["All","Simulation","Paper","Demo","Live"]),("Fuente",self.source,["All","Telegram","Manual"])):
            if items:field.addItems(items)
            filters.addWidget(QLabel(label)); filters.addWidget(field)
        refresh=QPushButton("Actualizar"); refresh.clicked.connect(self.refresh); filters.addWidget(refresh); filters.addStretch()
        for kind,label in (("csv","CSV"),("xlsx","Excel"),("pdf","PDF")):
            button=QPushButton(label); button.clicked.connect(lambda checked=False,k=kind:self.export(k)); filters.addWidget(button)
        layout.addLayout(filters); scroll=QScrollArea(); scroll.setWidgetResizable(True); content=QWidget(); body=QVBoxLayout(content); self.cards=QGridLayout(); body.addLayout(self.cards); self.charts=QGridLayout(); body.addLayout(self.charts); scroll.setWidget(content); layout.addWidget(scroll,3)
        self.tables=QTableWidget(); self.tables.setColumnCount(5); self.tables.setHorizontalHeaderLabels(["Grupo","Trades","Neto","Win rate","Tipo"]); self.tables.setMaximumHeight(210); layout.addWidget(self.tables)
        chart_titles=("Curva de balance","Curva de equity","Curva de drawdown","P/L diario","P/L mensual","Distribución ganancia/pérdida","Resultados por símbolo","Resultados por día","Resultados por hora","Distribución TP1/TP2/TP3/SL")
        self.chart_widgets={title:ChartWidget(title) for title in chart_titles}
        for index,widget in enumerate(self.chart_widgets.values()):self.charts.addWidget(widget,index//2,index%2)
    def filters(self): return {"start":self.start.date().toPython(),"end":self.end.date().toPython(),"profile":None if self.profile.currentText()=="All" else self.profile.currentText(),"symbol":None if self.symbol.currentText()=="All" else self.symbol.currentText(),"account":None if self.account.currentText()=="All" else self.account.currentText(),"mode":self.mode.currentText(),"source":self.source.currentText()}
    def refresh(self):
        current=self.profile.currentText(); self.profile.clear(); self.profile.addItem("All"); [self.profile.addItem(str(p.id)) for p in profile_repository.get_all()]; self.profile.setCurrentText(current or "All")
        metrics=trading_analytics_service.metrics(self.filters()); series=trading_analytics_service.series(self.filters()); labels=(("P/L neto","net"),("Ganancia bruta","gross_profit"),("Pérdida bruta","gross_loss"),("Tasa de aciertos","win_rate"),("Factor de ganancia","profit_factor"),("Expectativa","expectancy"),("Total operaciones","total"),("Operación promedio","average_trade"),("Drawdown máximo","maximum_drawdown"),("Racha actual","current_streak"),("Mejor racha","best_streak"),("Duración promedio","average_duration"))
        while self.cards.count(): item=self.cards.takeAt(0); item.widget().deleteLater() if item.widget() else None
        for index,(label,key) in enumerate(labels): card=QLabel(f"{label}\n{metrics[key]}"); card.setAlignment(Qt.AlignCenter); set_visual_role(card,"metricCard"); self.cards.addWidget(card,index//4,index%4)
        curve=dict((str(i),point[1]) for i,point in enumerate(metrics["curve"])); drawdown=dict((str(i),-point[2]) for i,point in enumerate(metrics["curve"])); mapping={"Curva de balance":curve,"Curva de equity":curve,"Curva de drawdown":drawdown,"P/L diario":series["daily"],"P/L mensual":series["monthly"],"Distribución ganancia/pérdida":{"Ganancias":metrics["gross_profit"],"Pérdidas":metrics["gross_loss"]},"Resultados por símbolo":series["symbol"],"Resultados por día":series["weekday"],"Resultados por hora":series["hour"],"Distribución TP1/TP2/TP3/SL":series["result"]}
        for title,values in mapping.items(): self.chart_widgets[title].set_values(values)
        table=[]; performance=trading_analytics_service.tables(self.filters())
        for kind in ("symbol","profile","mode"):
            for row in performance[kind]: table.append((row["name"],row["trades"],row["net"],row["win_rate"],kind))
        for kind in ("best_trades","worst_trades"):
            for row in performance[kind]: table.append((row["symbol"],1,row["net"],100 if row["net"]>0 else 0,kind))
        for kind in ("best_days","worst_days"):
            for name,value in performance[kind]: table.append((name,1,value,100 if value>0 else 0,kind))
        self.tables.setRowCount(len(table));
        for row,values in enumerate(table):
            for col,value in enumerate(values):self.tables.setItem(row,col,QTableWidgetItem(str(value)))
    def export(self,kind):
        path,_=QFileDialog.getSaveFileName(self,"Exportar analíticas",f"analytics.{kind}")
        if path: trading_analytics_service.export(self.filters(),path,kind)
