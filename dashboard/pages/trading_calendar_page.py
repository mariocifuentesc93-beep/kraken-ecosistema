import calendar
from datetime import date
from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QGridLayout, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QSpinBox, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget, QFileDialog, QDialog)

from dashboard.ui_theme import set_visual_role
from repositories.profile_repository import profile_repository
from services.trading_calendar_service import trading_calendar_service


class TradingCalendarPage(QWidget):
    def __init__(self):
        super().__init__(); self.current=date.today(); self.selected_day=None; self.build_ui(); self.refresh()

    def build_ui(self):
        layout=QVBoxLayout(self); layout.setSpacing(6)
        nav=QHBoxLayout(); self.previous=QPushButton("Anterior"); self.next=QPushButton("Siguiente"); today=QPushButton("Hoy"); self.month=QComboBox(); self.month.addItems(list(calendar.month_name)[1:]); self.year=QSpinBox(); self.year.setRange(2000,2100)
        for widget in (self.previous,self.next,today,QLabel("Mes"),self.month,self.year): nav.addWidget(widget)
        nav.addStretch(); self.demo=QPushButton("Cargar datos de demostración"); self.delete_demo=QPushButton("Eliminar demostración"); self.heatmap=QPushButton("Mapa anual"); nav.addWidget(self.demo); nav.addWidget(self.delete_demo); nav.addWidget(self.heatmap); layout.addLayout(nav)
        filters=QHBoxLayout(); self.profile=QComboBox(); self.symbol=QComboBox(); self.account=QComboBox(); self.mode=QComboBox(); self.source=QComboBox(); self.status=QComboBox(); self.direction=QComboBox(); self.result=QComboBox()
        for label,field,values in (("Perfil",self.profile,["All"]),("Símbolo",self.symbol,["All"]),("Cuenta",self.account,["All"]),("Modo",self.mode,["All","Simulation","Paper","Demo","Live"]),("Fuente",self.source,["All","Telegram","Manual"])):
            field.addItems(values); field.setMaximumWidth(140); filters.addWidget(QLabel(label)); filters.addWidget(field)
        for label,field in (("Estado",self.status),("Dirección",self.direction),("Resultado",self.result)):
            field.setMaximumWidth(140); filters.addWidget(QLabel(label)); filters.addWidget(field)
        filters.addStretch()
        for kind,label in (("csv","CSV"),("xlsx","Excel"),("pdf","PDF")):
            button=QPushButton(label); button.clicked.connect(partial(self.export,kind)); filters.addWidget(button)
        layout.addLayout(filters); self.summary=QLabel(); self.summary.setWordWrap(True); set_visual_role(self.summary,"information"); layout.addWidget(self.summary)
        workspace=QHBoxLayout(); calendar_widget=QWidget(); self.grid=QGridLayout(calendar_widget); self.grid.setSpacing(4); workspace.addWidget(calendar_widget,8); self.detail=QTableWidget(); self.detail.setColumnCount(11); self.detail.setHorizontalHeaderLabels(["Hora","Símbolo","Lado","Entrada","Salida","Lote","Riesgo","Bruto","Costes","Neto","Resultado"]); workspace.addWidget(self.detail,5); layout.addLayout(workspace,3)
        self.list=QTableWidget(); self.list.setColumnCount(7); self.list.setHorizontalHeaderLabels(["Fecha","Símbolo","Lado","Neto","Resultado","Modo","Perfil"]); self.list.setMaximumHeight(175); layout.addWidget(self.list,1)
        self.previous.clicked.connect(lambda:self.shift(-1)); self.next.clicked.connect(lambda:self.set_date(date.today())); today.clicked.connect(lambda:self.set_date(date.today())); self.demo.clicked.connect(self.load_demo); self.delete_demo.clicked.connect(self.remove_demo); self.heatmap.clicked.connect(self.show_heatmap)
        self.month.currentIndexChanged.connect(self.refresh); self.year.valueChanged.connect(self.refresh)
        for field in (self.profile,self.symbol,self.account,self.mode,self.source,self.status,self.direction,self.result): field.currentIndexChanged.connect(self.refresh)

    def set_date(self,value): self.current=value; self.month.setCurrentIndex(value.month-1); self.year.setValue(value.year); self.refresh()
    def shift(self,delta): month=self.current.month+delta; self.set_date(date(self.current.year+(month>12)-(month<1),12 if month<1 else 1 if month>12 else month,1))
    @staticmethod
    def _fill(combo,items):
        selected=combo.currentData(); combo.blockSignals(True); combo.clear(); combo.addItem("Todos",None)
        for label,value in items: combo.addItem(str(label),value)
        index=combo.findData(selected); combo.setCurrentIndex(index if index>=0 else 0); combo.blockSignals(False)
    def filters(self): return {"profile":self.profile.currentData(),"symbol":self.symbol.currentData(),"account":self.account.currentData(),"mode":self.mode.currentData(),"source":self.source.currentData(),"status":self.status.currentData(),"direction":self.direction.currentData(),"result":self.result.currentData()}

    def refresh(self,*args):
        self.year.blockSignals(True); self.year.setValue(self.current.year); self.year.blockSignals(False); self.month.blockSignals(True); self.month.setCurrentIndex(self.current.month-1); self.month.blockSignals(False)
        options=trading_calendar_service.filter_options()
        self._fill(self.profile,[(name,identifier) for identifier,name in options["profiles"]]); self._fill(self.account,[(name,identifier) for identifier,name in options["accounts"]])
        for combo,key in ((self.symbol,"symbols"),(self.mode,"modes"),(self.source,"sources"),(self.status,"statuses"),(self.direction,"directions"),(self.result,"results")): self._fill(combo,[(value,value) for value in options[key]])
        self.demo.setVisible(trading_calendar_service.demo_allowed()); self.delete_demo.setVisible(bool(trading_calendar_service.has_records()))
        daily=trading_calendar_service.daily(self.current.year,self.current.month,self.filters()); stats=trading_calendar_service.statistics(self.current.year,self.current.month,self.filters())
        self.summary.setText(f"P/L neto: {stats['net']:.2f} | Ganancia bruta: {stats['gross_profit']:.2f} | Pérdida bruta: {stats['gross_loss']:.2f} | Win rate: {stats['win_rate']}% | Factor: {stats['profit_factor']} | Trades: {stats['total']} | Ganadores: {stats['wins']} | Perdedoras: {stats['losses']} | Media: {stats['average']:.2f} | Mejor día: {stats['best_day']:.2f} | Peor día: {stats['worst_day']:.2f} | DD: {stats['drawdown']:.2f} | Saldo inicial/final: {stats['starting_balance']:.2f}/{stats['ending_balance']:.2f}")
        while self.grid.count(): item=self.grid.takeAt(0); item.widget().deleteLater() if item.widget() else None
        for col,name in enumerate(("Lun","Mar","Mié","Jue","Vie","Sáb","Dom")): header=QLabel(name); header.setAlignment(Qt.AlignCenter); self.grid.addWidget(header,0,col)
        first=calendar.monthrange(self.current.year,self.current.month)[0]; days=calendar.monthrange(self.current.year,self.current.month)[1]
        for day in range(1,days+1):
            bucket=daily[day]; current=(self.current.year,self.current.month,day)==(date.today().year,date.today().month,date.today().day); selected_day=day==self.selected_day; marker=" •" if bucket['open'] or bucket['pending'] else ""; button=QPushButton(f"{day}\n{bucket['net']:+.2f}\n{bucket['closed']} cerradas{marker}"); button.setToolTip("• indica operación abierta o pendiente"); button.setMinimumHeight(56); button.setProperty("calendarState","positive" if bucket['net']>0 else "negative" if bucket['net']<0 else "neutral"); button.setProperty("calendarSelected",selected_day); button.setProperty("calendarCurrent",current); button.clicked.connect(partial(self.select_day,day,bucket)); self.grid.addWidget(button,1+(first+day-1)//7,(first+day-1)%7)
        rows=trading_calendar_service.records(self.current.year,self.current.month,self.filters()); self.list.setRowCount(len(rows))
        for row,trade in enumerate(rows):
            for col,value in enumerate((trade['date'],trade['symbol'],trade['direction'],trade['net'],trade['result'],trade['mode'],trade['profile_name'])): self.list.setItem(row,col,QTableWidgetItem(str(value)))

    def select_day(self,day,bucket):
        self.selected_day=day; self.detail.setRowCount(len(bucket['trades']))
        for row,trade in enumerate(bucket['trades']):
            for col,value in enumerate((trade['opened_at'],trade['symbol'],trade['direction'],trade['entry'],trade['exit'],trade['volume'],trade['risk'],trade['gross'],trade['costs'],trade['net'],trade['result'])): self.detail.setItem(row,col,QTableWidgetItem(str(value)))
        self.refresh()

    def load_demo(self):
        if QMessageBox.question(self,"Datos de demostración","¿Insertar datos demo deterministas en este mes?",QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes:return
        trading_calendar_service.load_demo(self.current.year,self.current.month); self.refresh()
    def remove_demo(self):
        if QMessageBox.question(self,"Eliminar demostración","¿Eliminar únicamente los registros demo?",QMessageBox.Yes|QMessageBox.No)==QMessageBox.Yes: trading_calendar_service.delete_demo(); self.selected_day=None; self.refresh()
    def export(self,kind):
        suffix={"csv":"csv","xlsx":"xlsx","pdf":"pdf"}[kind]; path,_=QFileDialog.getSaveFileName(self,"Exportar calendario",f"trading_calendar.{suffix}")
        if not path:return
        rows=trading_calendar_service.records(self.current.year,self.current.month,self.filters())
        if kind=="csv":trading_calendar_service.export_csv(rows,path)
        elif kind=="xlsx":trading_calendar_service.export_excel(rows,path)
        else:trading_calendar_service.export_pdf(trading_calendar_service.statistics(self.current.year,self.current.month,self.filters()),path)

    def show_heatmap(self):
        dialog=QDialog(self); dialog.setWindowTitle("Mapa anual de rentabilidad"); dialog.resize(1150,520); grid=QGridLayout(dialog); data=trading_calendar_service.annual_heatmap(self.year.value(),self.filters())
        for month in range(1,13):
            grid.addWidget(QLabel(calendar.month_abbr[month]),month,0)
            for day in range(1,32):
                value=data.get((month,day)); cell=QLabel("" if value is None else f"{value:+.0f}"); cell.setAlignment(Qt.AlignCenter); cell.setProperty("calendarState","positive" if value and value>0 else "negative" if value and value<0 else "neutral"); grid.addWidget(cell,month,day)
        dialog.exec()
