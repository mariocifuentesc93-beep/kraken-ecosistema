import json
from datetime import date
from pathlib import Path

from database.database_manager import database_manager


class TradeReplayService:
    """Builds replay sessions from persisted history only; never sends orders."""
    def session(self, day, filters=None):
        filters=filters or {}; target=day.isoformat() if isinstance(day,date) else str(day)[:10]
        clauses=["substr(COALESCE(o.closed_at,o.opened_at),1,10)=?"]; params=[target]
        for column,key in (("o.profile_id","profile"),("o.symbol","symbol")):
            if filters.get(key): clauses.append(f"{column}=?"); params.append(filters[key])
        operations=database_manager.execute("SELECT o.*,s.raw_message,s.status signal_status,s.source FROM operations o LEFT JOIN signals s ON s.id=o.signal_id WHERE "+" AND ".join(clauses)+" ORDER BY COALESCE(o.opened_at,o.closed_at)",params).fetchall()
        events=[]
        for operation in operations:
            op=dict(operation); mode_events=database_manager.execute("SELECT * FROM operation_events WHERE operation_id=? ORDER BY id",(op["id"],)).fetchall(); mode=str(mode_events[-1]["execution_mode"] if mode_events else "Simulation")
            if filters.get("mode") and filters["mode"].lower() not in ("all",mode.lower()):continue
            if op.get("raw_message"):
                events.append(self._event(op,"SIGNAL",op.get("opened_at"),"Incoming Telegram signal",raw=op["raw_message"],mode=mode))
            else:
                # Older operations may not be linked to their persisted signal.
                # Keep the replay chronological and explicit without inventing a
                # Telegram message that was never stored.
                events.append(self._event(op,"SIGNAL",op.get("opened_at"),"Historical signal (raw message unavailable)",mode=mode))
            for row in mode_events:
                item=dict(row); events.append(self._event(op,item.get("new_state") or item["event"],item["created_at"],item.get("description","") or "State transition",mode=mode))
            for row in database_manager.execute("SELECT * FROM simulation_price_events WHERE operation_id=? ORDER BY id",(op["id"],)).fetchall():
                item=dict(row); events.append(self._event(op,"PRICE",item["created_at"],item["event"],price=item.get("last_price"),bid=item.get("bid"),ask=item.get("ask"),mode=mode))
        papers=database_manager.execute("SELECT * FROM paper_trades WHERE substr(COALESCE(closed_at,opened_at),1,10)=? ORDER BY COALESCE(opened_at,closed_at)",(target,)).fetchall()
        for row in papers:
            item=dict(row); metadata=json.loads(item.get("metadata") or "{}");
            if filters.get("profile") and str(item.get("profile_id"))!=str(filters["profile"]):continue
            if filters.get("symbol") and item.get("symbol")!=filters["symbol"]:continue
            if filters.get("mode") not in (None,"All","Paper"):continue
            events.append({"time":item.get("opened_at") or item.get("closed_at"),"type":"SIGNAL","state":"PAPER_SIGNAL","description":"Paper trade signal","operation_id":item.get("operation_id"),"symbol":item["symbol"],"profile_id":item.get("profile_id"),"direction":item["direction"],"price":item.get("entry_price"),"pnl":0,"balance":None,"mode":"Paper","raw":""})
            events.append({"time":item.get("closed_at") or item.get("opened_at"),"type":"STATE","state":metadata.get("result",item["status"]),"description":"Paper trade result","operation_id":item.get("operation_id"),"symbol":item["symbol"],"profile_id":item.get("profile_id"),"direction":item["direction"],"price":None,"pnl":item.get("net_pl",0),"balance":None,"mode":"Paper","raw":""})
        events.sort(key=lambda event:event.get("time") or "")
        balance=0
        for event in events:
            balance+=float(event.get("pnl") or 0); event["balance"]=round(balance,2)
        return {"date":target,"events":events,"operations":len(operations),"paper_events":len([e for e in events if e["mode"]=="Paper"])}
    @staticmethod
    def _event(operation,state,time,description,price=None,bid=None,ask=None,raw="",mode="Simulation"):
        event_type = "PRICE" if state == "PRICE" else "SIGNAL" if state == "SIGNAL" else "STATE"
        return {"time":time,"type":event_type,"state":state,"description":description,"operation_id":operation["id"],"symbol":operation.get("symbol"),"profile_id":operation.get("profile_id"),"direction":operation.get("direction"),"price":price,"bid":bid,"ask":ask,"pnl":operation.get("profit",0) if state in ("CLOSED","TP1","TP2","TP3","SL") else 0,"balance":None,"mode":mode,"raw":raw}
    @staticmethod
    def state_index(events,state): return next((index for index,event in enumerate(events) if event["state"]==state),-1)
    def export_json(self,session,path): Path(path).write_text(json.dumps(session,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
    def export_pdf(self,session,path):
        text=f"Kraken Bot Replay | {session['date']} | {len(session['events'])} events"; content=f"BT /F1 12 Tf 50 750 Td ({text}) Tj ET"; pdf=f"%PDF-1.4\n1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n2 0 obj<< /Type /Pages /Kids[3 0 R] /Count 1 >>endobj\n3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox[0 0 612 792] /Resources<< /Font<< /F1 4 0 R >> >> /Contents 5 0 R >>endobj\n4 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n5 0 obj<< /Length {len(content)} >>stream\n{content}\nendstream endobj\ntrailer<< /Root 1 0 R >>\n%%EOF"; Path(path).write_bytes(pdf.encode("latin-1","replace"))


trade_replay_service=TradeReplayService()
