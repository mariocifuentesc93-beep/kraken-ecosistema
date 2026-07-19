from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QMessageBox, QLineEdit, QCheckBox
from repositories.profile_repository import profile_repository
from trading.paper_trading_engine import paper_trading_engine


class PaperTradingPage(QWidget):
    def __init__(self):
        super().__init__(); layout=QVBoxLayout(self); settings=QHBoxLayout(); self.start=QLineEdit(); self.currency=QLineEdit(); self.slippage=QLineEdit(); self.commission=QLineEdit(); self.fallback=QCheckBox("Permitir fallback"); save=QPushButton("Guardar cuenta virtual"); save.clicked.connect(self.save_settings)
        for label,field in (("Saldo inicial",self.start),("Moneda",self.currency),("Slippage",self.slippage),("Comisión",self.commission)): settings.addWidget(QLabel(label)); settings.addWidget(field)
        settings.addWidget(self.fallback); settings.addWidget(save); layout.addLayout(settings); bar=QHBoxLayout(); self.summary=QLabel(); bar.addWidget(self.summary); bar.addStretch(); refresh=QPushButton("Actualizar"); refresh.clicked.connect(self.refresh); reset=QPushButton("Reiniciar cuenta virtual"); reset.clicked.connect(self.reset); bar.addWidget(refresh); bar.addWidget(reset); layout.addLayout(bar); self.table=QTableWidget(); self.table.setColumnCount(7); self.table.setHorizontalHeaderLabels(["ID","Símbolo","Dirección","Estado","Lote","Neto","Resultado"]); self.table.setEditTriggers(QTableWidget.NoEditTriggers); layout.addWidget(self.table); self.refresh()
    def refresh(self):
        profile=profile_repository.get_active()
        if not profile: self.summary.setText("Seleccione un perfil activo."); self.table.setRowCount(0); return
        data=paper_trading_engine.summary(profile.id); a=data["account"]; self.start.setText(str(a["starting_balance"])); self.currency.setText(a["currency"]); self.slippage.setText(str(a["slippage"])); self.commission.setText(str(a["commission"])); self.fallback.setChecked(bool(a["allow_fallback"])); self.summary.setText(f"Balance: {a['balance']:.2f} {a['currency']} | Equity: {a['equity']:.2f} | Abiertas: {data['open']} | Pendientes: {data['pending']} | Cerradas: {data['closed']} | P/L diario: {data['daily_pl']:.2f} | Win rate: {data['win_rate']}% | DD: {data['drawdown']:.2f}"); self.table.setRowCount(len(data["trades"]))
        for row,t in enumerate(data["trades"]):
            for col,value in enumerate((t["id"],t["symbol"],t["direction"],t["status"],t["volume"],t["net_pl"],t["metadata"].get("result",""))): self.table.setItem(row,col,QTableWidgetItem(str(value)))
    def reset(self):
        profile=profile_repository.get_active()
        if profile and QMessageBox.question(self,"Paper trading","¿Reiniciar cuenta virtual y eliminar operaciones?",QMessageBox.Yes|QMessageBox.No)==QMessageBox.Yes: paper_trading_engine.reset(profile.id); self.refresh()
    def save_settings(self):
        profile=profile_repository.get_active()
        if not profile:return
        try: paper_trading_engine.configure(profile.id,starting_balance=float(self.start.text()),currency=self.currency.text() or "USD",slippage=float(self.slippage.text()),commission=float(self.commission.text()),allow_fallback=self.fallback.isChecked()); self.refresh()
        except ValueError: QMessageBox.warning(self,"Paper trading","Revise los valores de la cuenta virtual.")
