from datetime import date

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (QComboBox, QDateEdit, QGridLayout, QHBoxLayout, QLabel, QPushButton,
                               QSlider, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QFileDialog)
from repositories.profile_repository import profile_repository
from repositories.symbol_repository import symbol_repository
from services.trade_replay_service import trade_replay_service


class ReplayPage(QWidget):
    def __init__(self):
        super().__init__(); self.events=[]; self.index=0; self.timer=QTimer(self); self.timer.timeout.connect(self.next_event); self.build_ui(); self.load_session()
    def build_ui(self):
        layout=QVBoxLayout(self); filters=QGridLayout(); self.day=QDateEdit(); self.day.setDate(date.today()); self.profile=QComboBox(); self.symbol=QComboBox(); self.mode=QComboBox(); self.speed=QComboBox(); self.mode.addItems(["All","Simulation","Paper","Demo","Live"]); self.speed.addItems(["x1","x2","x5","x10","x25","x50"])
        for column,(label,widget) in enumerate((("Fecha",self.day),("Perfil",self.profile),("Símbolo",self.symbol),("Modo",self.mode),("Velocidad",self.speed))): filters.addWidget(QLabel(label),0,column); filters.addWidget(widget,1,column); filters.setColumnStretch(column,1)
        load=QPushButton("Cargar replay"); load.clicked.connect(self.load_session); filters.addWidget(load,2,0)
        for kind,label in (("json","JSON"),("pdf","PDF")):
            button=QPushButton(label); button.clicked.connect(lambda checked=False,k=kind:self.export(k)); filters.addWidget(button,2,1 if kind=="json" else 2)
        layout.addLayout(filters); controls=QGridLayout()
        for index,(label,handler) in enumerate((("Play",self.play),("Pause",self.pause),("Stop",self.stop),("Anterior",self.previous_event),("Siguiente",self.next_event))):
            button=QPushButton(label); button.clicked.connect(handler); controls.addWidget(button,0,index)
        self.state_jump=QComboBox(); self.state_jump.currentTextChanged.connect(self.jump_state); controls.addWidget(QLabel("Ir a estado"),1,0); controls.addWidget(self.state_jump,1,1,1,4); layout.addLayout(controls)
        self.slider=QSlider(Qt.Horizontal); self.slider.valueChanged.connect(self.scrub); layout.addWidget(self.slider); self.status=QLabel("Sin eventos"); layout.addWidget(self.status)
        self.timeline=QTableWidget(); self.timeline.setColumnCount(6); self.timeline.setHorizontalHeaderLabels(["Hora","Tipo","Estado","Símbolo","Precio","Descripción"]); self.timeline.setEditTriggers(QTableWidget.NoEditTriggers); layout.addWidget(self.timeline)
        panels=QHBoxLayout(); self.price=QLabel("Precio: —"); self.position=QLabel("Posición: —"); self.pnl=QLabel("P/L: 0.00"); self.balance=QLabel("Balance: 0.00")
        for panel in (self.price,self.position,self.pnl,self.balance): panels.addWidget(panel)
        layout.addLayout(panels)
    def filters(self): return {"profile":None if self.profile.currentText()=="All" else self.profile.currentText(),"symbol":None if self.symbol.currentText()=="All" else self.symbol.currentText(),"mode":self.mode.currentText()}
    def load_session(self):
        current=self.profile.currentText(); self.profile.clear(); self.profile.addItem("All"); profiles=profile_repository.get_all(); [self.profile.addItem(str(p.id)) for p in profiles]; self.profile.setCurrentText(current or "All")
        selected_symbol=self.symbol.currentText(); self.symbol.clear(); self.symbol.addItem("All")
        symbols=sorted({symbol.symbol for profile in profiles for symbol in symbol_repository.get_all(profile.id)})
        self.symbol.addItems(symbols); self.symbol.setCurrentText(selected_symbol or "All")
        self.session=trade_replay_service.session(self.day.date().toPython(),self.filters()); self.events=self.session["events"]; self.index=0; self.slider.setRange(0,max(0,len(self.events)-1)); self.state_jump.blockSignals(True); self.state_jump.clear(); self.state_jump.addItems(sorted({event["state"] for event in self.events})); self.state_jump.blockSignals(False); self.populate(); self.show_event()
    def populate(self):
        self.timeline.setRowCount(len(self.events))
        for row,event in enumerate(self.events):
            for col,value in enumerate((event.get("time"),event["type"],event["state"],event.get("symbol"),event.get("price"),event["description"])): self.timeline.setItem(row,col,QTableWidgetItem(str(value or "")))
    def show_event(self):
        if not self.events: self.status.setText("No hay historial para los filtros seleccionados."); return
        event=self.events[self.index]; self.status.setText(f"Evento {self.index+1}/{len(self.events)} · {event['state']}"); self.timeline.selectRow(self.index); self.slider.blockSignals(True); self.slider.setValue(self.index); self.slider.blockSignals(False); self.price.setText(f"Precio: {event.get('price') or '—'}"); self.position.setText(f"Posición: {event.get('direction') or '—'} {event.get('symbol') or ''}"); self.pnl.setText(f"P/L: {event.get('pnl',0):.2f}"); self.balance.setText(f"Balance: {event.get('balance',0):.2f}")
    def play(self): self.timer.start(max(30,1000//int(self.speed.currentText()[1:])))
    def pause(self): self.timer.stop()
    def stop(self): self.pause(); self.index=0; self.show_event()
    def next_event(self):
        if self.index>=len(self.events)-1: self.pause()
        else: self.index+=1; self.show_event()
    def previous_event(self): self.index=max(0,self.index-1); self.show_event()
    def scrub(self,value): self.index=value; self.show_event()
    def jump_state(self,state):
        index=trade_replay_service.state_index(self.events,state)
        if index>=0: self.index=index; self.show_event()
    def export(self,kind):
        path,_=QFileDialog.getSaveFileName(self,"Exportar replay",f"replay.{kind}")
        if path: (trade_replay_service.export_json if kind=="json" else trade_replay_service.export_pdf)(self.session,path)
