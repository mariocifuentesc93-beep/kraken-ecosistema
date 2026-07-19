import calendar
from datetime import date
from functools import partial
from pathlib import Path

from PySide6.QtWidgets import (QComboBox, QGridLayout, QHBoxLayout, QLabel, QPushButton,
                               QSpinBox, QSplitter, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget, QFileDialog)
from dashboard.styles import CARD_COLOR, ERROR_COLOR, SUCCESS_COLOR, table_style
from repositories.profile_repository import profile_repository
from services.trading_calendar_service import trading_calendar_service


class TradingCalendarPage(QWidget):
    def __init__(self):
        super().__init__(); self.current=date.today(); self.build_ui(); self.refresh()
    def build_ui(self):
        layout=QVBoxLayout(self); nav=QHBoxLayout(); self.previous=QPushButton("◀"); self.next=QPushButton("▶"); today=QPushButton("Hoy"); self.month=QComboBox(); self.month.addItems(list(calendar.month_name)[1:]); self.year=QSpinBox(); self.year.setRange(2000,2100)
        for widget in (self.previous,self.next,today,self.month,self.year):nav.addWidget(widget)
        self.profile=QComboBox(); self.symbol=QComboBox(); self.account=QComboBox(); self.mode=QComboBox(); self.source=QComboBox()
        for label,field,values in (("Perfil",self.profile,["All"]),("Símbolo",self.symbol,["All"]),("Cuenta",self.account,["All"]),("Modo",self.mode,["All","Simulation","Paper","Demo","Live"]),("Fuente",self.source,["All","Telegram","Manual"])): field.addItems(values); nav.addWidget(QLabel(label)); nav.addWidget(field)
        for kind,label in (("csv","CSV"),("xlsx","Excel"),("pdf","PDF")):
            button=QPushButton(label); button.clicked.connect(partial(self.export,kind)); nav.addWidget(button)
        layout.addLayout(nav); self.summary=QLabel(); layout.addWidget(self.summary); splitter=QSplitter(); calendar_widget=QWidget(); self.grid=QGridLayout(calendar_widget); splitter.addWidget(calendar_widget); self.detail=QTableWidget(); self.detail.setColumnCount(11); self.detail.setHorizontalHeaderLabels(["Hora","Símbolo","Lado","Entrada","Salida","Lote","Riesgo","Bruto","Costes","Neto","Resultado"]); self.detail.setStyleSheet(table_style()); splitter.addWidget(self.detail); layout.addWidget(splitter); self.list=QTableWidget(); self.list.setColumnCount(7); self.list.setHorizontalHeaderLabels(["Fecha","Símbolo","Lado","Neto","Resultado","Modo","Perfil"]); self.list.setStyleSheet(table_style()); layout.addWidget(self.list)
        self.previous.clicked.connect(lambda:self.shift(-1)); self.next.clicked.connect(lambda:self.shift(1)); today.clicked.connect(lambda:self.set_date(date.today())); self.month.currentIndexChanged.connect(self.refresh); self.year.valueChanged.connect(self.refresh)
        for field in (self.profile,self.symbol,self.account,self.mode,self.source):field.currentIndexChanged.connect(self.refresh)
    def set_date(self,value): self.current=value; self.month.setCurrentIndex(value.month-1); self.year.setValue(value.year); self.refresh()
    def shift(self,delta): month=self.current.month+delta; self.set_date(date(self.current.year+(month>12)-(month<1),12 if month<1 else 1 if month>12 else month,1))
    def filters(self): return {"profile":None if self.profile.currentText()=="All" else self.profile.currentText(),"symbol":None if self.symbol.currentText()=="All" else self.symbol.currentText(),"account":None if self.account.currentText()=="All" else self.account.currentText(),"mode":self.mode.currentText(),"source":self.source.currentText()}
    def refresh(self,*args):
        if self.year.value()!=self.current.year:self.year.blockSignals(True);self.year.setValue(self.current.year);self.year.blockSignals(False)
        if self.month.currentIndex()!=self.current.month-1:self.month.blockSignals(True);self.month.setCurrentIndex(self.current.month-1);self.month.blockSignals(False)
        self.profile.blockSignals(True); self.profile.clear(); self.profile.addItem("All"); [self.profile.addItem(str(p.id)) for p in profile_repository.get_all()]; self.profile.blockSignals(False)
        daily=trading_calendar_service.daily(self.current.year,self.current.month,self.filters()); stats=trading_calendar_service.statistics(self.current.year,self.current.month,self.filters()); self.summary.setText(" | ".join(f"{key}: {value}" for key,value in stats.items()))
        while self.grid.count(): item=self.grid.takeAt(0); item.widget().deleteLater() if item.widget() else None
        for col,name in enumerate(("Lun","Mar","Mié","Jue","Vie","Sáb","Dom")):self.grid.addWidget(QLabel(name),0,col)
        first=calendar.monthrange(self.current.year,self.current.month)[0]; days=calendar.monthrange(self.current.year,self.current.month)[1]
        for day in range(1,days+1):
            bucket=daily[day]; button=QPushButton(f"{day}\n{bucket['net']:+.2f}\n{bucket['closed']} cerradas"+("\n●" if bucket['open'] or bucket['pending'] else "")); color=SUCCESS_COLOR if bucket['net']>0 else ERROR_COLOR if bucket['net']<0 else CARD_COLOR; button.setStyleSheet(f"QPushButton{{background:{color};min-height:64px;color:white;}}") ; button.clicked.connect(partial(self.select_day,day,bucket)); self.grid.addWidget(button,1+(first+day-1)//7,(first+day-1)%7)
        rows=trading_calendar_service.records(self.current.year,self.current.month,self.filters()); self.list.setRowCount(len(rows));
        for row,trade in enumerate(rows):
            for col,value in enumerate((trade['date'],trade['symbol'],trade['direction'],trade['net'],trade['result'],trade['mode'],trade['profile_id'])):self.list.setItem(row,col,QTableWidgetItem(str(value)))
    def select_day(self,day,bucket):
        self.detail.setRowCount(len(bucket['trades']))
        for row,trade in enumerate(bucket['trades']):
            for col,value in enumerate((trade['opened_at'],trade['symbol'],trade['direction'],trade['entry'],trade['exit'],trade['volume'],trade['risk'],trade['gross'],trade['costs'],trade['net'],trade['result'])):self.detail.setItem(row,col,QTableWidgetItem(str(value)))
    def export(self,kind):
        suffix={"csv":"csv","xlsx":"xlsx","pdf":"pdf"}[kind]; path,_=QFileDialog.getSaveFileName(self,"Exportar calendario",f"trading_calendar.{suffix}")
        if not path:return
        rows=trading_calendar_service.records(self.current.year,self.current.month,self.filters())
        if kind=="csv":trading_calendar_service.export_csv(rows,path)
        elif kind=="xlsx":trading_calendar_service.export_excel(rows,path)
        else:trading_calendar_service.export_pdf(trading_calendar_service.statistics(self.current.year,self.current.month,self.filters()),path)
