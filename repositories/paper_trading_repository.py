import json
from datetime import datetime
from database.database_manager import database_manager


class PaperTradingRepository:
    def account(self, profile_id, create=True):
        cursor = database_manager.cursor(); cursor.execute("SELECT * FROM paper_accounts WHERE profile_id=?", (profile_id,)); row = cursor.fetchone()
        if row or not create: return dict(row) if row else None
        now = datetime.now().isoformat(); cursor.execute("INSERT INTO paper_accounts(profile_id,starting_balance,balance,equity,currency,slippage,commission,allow_fallback,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)", (profile_id,10000,10000,10000,"USD",0,0,0,now,now)); database_manager.commit(); return self.account(profile_id, False)
    def save_account(self, account):
        account["updated_at"] = datetime.now().isoformat(); database_manager.execute("UPDATE paper_accounts SET starting_balance=?,balance=?,equity=?,currency=?,slippage=?,commission=?,allow_fallback=?,updated_at=? WHERE id=?", (account["starting_balance"],account["balance"],account["equity"],account["currency"],account["slippage"],account["commission"],int(account["allow_fallback"]),account["updated_at"],account["id"])); database_manager.commit(); return account
    def reset(self, profile_id):
        account=self.account(profile_id); account["balance"]=account["starting_balance"]; account["equity"]=account["starting_balance"]; self.save_account(account); database_manager.execute("DELETE FROM paper_trades WHERE paper_account_id=?",(account["id"],)); database_manager.commit(); return account
    def create_trade(self, trade):
        fields=("paper_account_id","operation_id","signal_key","profile_id","symbol","direction","status","volume","remaining_volume","entry_price","stop_loss","take_profits","gross_pl","spread_cost","slippage_cost","commission_cost","net_pl","initial_risk","margin_estimate","opened_at","closed_at","duration_seconds","updated_at","metadata")
        values=[json.dumps(trade[k]) if k in ("take_profits","metadata") else trade.get(k) for k in fields]
        cursor=database_manager.cursor(); cursor.execute(f"INSERT INTO paper_trades({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})",values); database_manager.commit(); return self.get_trade(cursor.lastrowid)
    def get_trade(self, trade_id):
        row=database_manager.execute("SELECT * FROM paper_trades WHERE id=?",(trade_id,)).fetchone(); return self._decode(row)
    def by_signal(self, key):
        row=database_manager.execute("SELECT * FROM paper_trades WHERE signal_key=?",(key,)).fetchone(); return self._decode(row)
    def trades(self, account_id, status=None):
        sql="SELECT * FROM paper_trades WHERE paper_account_id=?"; params=[account_id]
        if status: sql+=" AND status=?"; params.append(status)
        return [self._decode(row) for row in database_manager.execute(sql+" ORDER BY id DESC",params).fetchall()]
    def save_trade(self, trade):
        trade["updated_at"]=datetime.now().isoformat(); database_manager.execute("UPDATE paper_trades SET status=?,remaining_volume=?,entry_price=?,stop_loss=?,gross_pl=?,spread_cost=?,slippage_cost=?,commission_cost=?,net_pl=?,initial_risk=?,margin_estimate=?,opened_at=?,closed_at=?,duration_seconds=?,metadata=?,updated_at=? WHERE id=?",(trade["status"],trade["remaining_volume"],trade["entry_price"],trade["stop_loss"],trade["gross_pl"],trade["spread_cost"],trade["slippage_cost"],trade["commission_cost"],trade["net_pl"],trade["initial_risk"],trade["margin_estimate"],trade["opened_at"],trade["closed_at"],trade.get("duration_seconds",0),json.dumps(trade["metadata"]),trade["updated_at"],trade["id"])); database_manager.commit(); return trade
    @staticmethod
    def _decode(row):
        if not row:return None
        item=dict(row); item["take_profits"]=json.loads(item["take_profits"] or "[]"); item["metadata"]=json.loads(item["metadata"] or "{}"); return item


paper_trading_repository=PaperTradingRepository()
