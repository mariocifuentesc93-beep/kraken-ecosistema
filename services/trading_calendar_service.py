import calendar
import csv
import json
import os
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from database.database_manager import database_manager
from models.profile import Profile
from repositories.paper_trading_repository import paper_trading_repository
from repositories.profile_repository import profile_repository


class TradingCalendarService:
    """Read-only calendar projections over SQLite operation and paper-trade records."""
    def filter_options(self):
        """Return global reporting dimensions without depending on active profiles."""
        profiles = [
            (str(row["id"]), row["name"])
            for row in database_manager.execute(
                "SELECT id,name FROM profiles ORDER BY name"
            ).fetchall()
        ]
        accounts = [
            (str(row["id"]), row["name"])
            for row in database_manager.execute(
                "SELECT id,name FROM mt5_accounts ORDER BY name"
            ).fetchall()
        ]
        symbols = [
            row[0] for row in database_manager.execute(
                """
                SELECT DISTINCT symbol FROM (
                    SELECT symbol FROM operations
                    UNION ALL
                    SELECT symbol FROM paper_trades
                )
                WHERE COALESCE(symbol,'')<>''
                ORDER BY symbol
                """
            ).fetchall()
        ]
        return {
            "profiles": profiles,
            "accounts": accounts,
            "symbols": symbols,
            "modes": ["SIMULATION", "PAPER", "DEMO", "LIVE"],
            "sources": ["TELEGRAM", "INTERNAL", "MANUAL", "UNKNOWN"],
            "statuses": [
                "OPEN", "CLOSED", "REJECTED", "SIMULATION",
                "PENDING", "QUEUED",
            ],
            "directions": ["BUY", "SELL"],
            "results": [
                "WIN", "LOSS", "BREAKEVEN", "TP1", "TP2", "TP3",
                "SL", "REJECTED",
            ],
        }

    def records(self, year, month, filters=None):
        filters = filters or {}; first=f"{year:04d}-{month:02d}-01"; last=f"{year + (month==12):04d}-{(month%12)+1:02d}-01"
        operations=database_manager.execute("""
            SELECT
                o.*,
                p.name AS profile_name,
                a.name AS account_name,
                COALESCE(
                    NULLIF(UPPER(s.source), ''),
                    CASE
                        WHEN UPPER(COALESCE(p.signal_source_mode, '')) IN
                             ('TELEGRAM', 'INTERNAL')
                        THEN UPPER(p.signal_source_mode)
                        ELSE 'UNKNOWN'
                    END
                ) AS source,
                COALESCE(
                    (
                        SELECT NULLIF(UPPER(e.execution_mode), '')
                        FROM operation_events e
                        WHERE e.operation_id=o.id
                        ORDER BY e.id DESC
                        LIMIT 1
                    ),
                    CASE
                        WHEN UPPER(COALESCE(o.status, ''))='SIMULATION'
                             OR COALESCE(o.ticket, -1)=0
                        THEN 'SIMULATION'
                        WHEN o.ticket IS NOT NULL AND o.ticket>0
                             AND UPPER(COALESCE(p.execution_mode, ''))
                                 IN ('DEMO', 'LIVE')
                        THEN UPPER(p.execution_mode)
                        ELSE UPPER(COALESCE(p.execution_mode, 'UNKNOWN'))
                    END
                ) AS mode
            FROM operations o
            LEFT JOIN signals s ON s.id=o.signal_id
            LEFT JOIN profiles p ON p.id=o.profile_id
            LEFT JOIN mt5_accounts a ON a.id=o.mt5_account_id
            WHERE COALESCE(o.closed_at,o.opened_at,o.updated_at)>=?
              AND COALESCE(o.closed_at,o.opened_at,o.updated_at)<?
        """,(first,last)).fetchall()
        papers=database_manager.execute("SELECT * FROM paper_trades WHERE COALESCE(closed_at,opened_at)>=? AND COALESCE(closed_at,opened_at)<?",(first,last)).fetchall()
        rows=[]
        for row in operations:
            r=dict(row)
            profit=float(r.get("profit",0) or 0)
            result=r.get("result")
            if not result and str(r.get("status") or "").upper()=="CLOSED":
                result="WIN" if profit>0 else "LOSS" if profit<0 else "BREAKEVEN"
            rows.append({
                "id":f"O{r['id']}",
                "date":r.get("closed_at") or r.get("opened_at") or r.get("updated_at"),
                "profile_id":r.get("profile_id"),
                "profile_name":r.get("profile_name") or f"Perfil {r.get('profile_id')}",
                "account_id":r.get("mt5_account_id"),
                "account_name":r.get("account_name") or f"Cuenta {r.get('mt5_account_id')}",
                "symbol":r.get("symbol"),
                "direction":str(r.get("direction") or "").upper(),
                "entry":r.get("entry_price"),
                "exit":r.get("exit_price"),
                "volume":r.get("volume"),
                "risk":0,
                "gross":profit,
                "costs":0,
                "net":profit,
                "result":result or r.get("status"),
                "status":str(r.get("status") or "").upper(),
                "mode":str(r.get("mode") or "UNKNOWN").upper(),
                "source":str(r.get("source") or "UNKNOWN").upper(),
                "opened_at":r.get("opened_at"),
                "closed_at":r.get("closed_at"),
                "ticket":r.get("ticket"),
            })
        for row in papers:
            r=dict(row); metadata=json.loads(r.get("metadata") or "{}"); rows.append({"id":f"P{r['id']}","date":r.get("closed_at") or r.get("opened_at"),"profile_id":r.get("profile_id"),"profile_name":f"Perfil {r.get('profile_id')}","account_id":None,"account_name":"Paper","symbol":r.get("symbol"),"direction":str(r.get("direction") or "").upper(),"entry":r.get("entry_price"),"exit":None,"volume":r.get("volume"),"risk":r.get("initial_risk",0),"gross":r.get("gross_pl",0),"costs":sum(r.get(k,0) or 0 for k in ("spread_cost","slippage_cost","commission_cost")),"net":r.get("net_pl",0),"result":metadata.get("result",r.get("status")),"status":str(r.get("status") or "").upper(),"mode":"PAPER","source":str(metadata.get("source","TELEGRAM")).upper(),"opened_at":r.get("opened_at"),"closed_at":r.get("closed_at"),"ticket":None})
        return [r for r in rows if self._matches(r,filters)]
    @staticmethod
    def _matches(row,f):
        def same(key, value):
            return not value or str(value).upper() in ("ALL", "TODOS") or str(row.get(key, "")).upper()==str(value).upper()
        return (
            same("profile_id",f.get("profile"))
            and same("symbol",f.get("symbol"))
            and same("account_id",f.get("account"))
            and same("mode",f.get("mode"))
            and same("source",f.get("source"))
            and same("status",f.get("status"))
            and same("direction",f.get("direction"))
            and same("result",f.get("result"))
        )
    def daily(self,year,month,filters=None):
        data={day:{"net":0.0,"closed":0,"open":0,"pending":0,"trades":[]} for day in range(1,calendar.monthrange(year,month)[1]+1)}
        for r in self.records(year,month,filters):
            if not r["date"]:continue
            day=datetime.fromisoformat(str(r["date"]).replace("Z","+00:00")).day; bucket=data[day]; bucket["trades"].append(r)
            if r["status"]=="CLOSED": bucket["closed"]+=1; bucket["net"]+=float(r["net"])
            elif r["status"]=="OPEN": bucket["open"]+=1
            elif r["status"] in ("PENDING","QUEUED"): bucket["pending"]+=1
        return data
    def statistics(self,year,month,filters=None):
        rows=self.records(year,month,filters); closed=[r for r in rows if r["status"]=="CLOSED"]; values=[float(r["net"]) for r in closed]; wins=[v for v in values if v>0]; losses=[v for v in values if v<0]; days=self.daily(year,month,filters); daily_values=[v["net"] for v in days.values() if v["closed"]]
        gross_profit=sum(wins); gross_loss=sum(losses); cumulative=peak=drawdown=0
        for value in daily_values: cumulative+=value; peak=max(peak,cumulative); drawdown=max(drawdown,peak-cumulative)
        accounts=database_manager.execute("SELECT COALESCE(SUM(starting_balance),0),COALESCE(SUM(balance),0) FROM paper_accounts").fetchone()
        return {"net":round(sum(values),2),"gross_profit":round(gross_profit,2),"gross_loss":round(gross_loss,2),"win_rate":round(len(wins)/len(closed)*100,2) if closed else 0,"profit_factor":round(gross_profit/abs(gross_loss),2) if gross_loss else 0,"total":len(closed),"wins":len(wins),"losses":len(losses),"average":round(sum(values)/len(values),2) if values else 0,"best_day":max(daily_values,default=0),"worst_day":min(daily_values,default=0),"drawdown":round(drawdown,2),"starting_balance":accounts[0],"ending_balance":accounts[1]}
    def annual_heatmap(self,year,filters=None):
        return {(month,day):value["net"] for month in range(1,13) for day,value in self.daily(year,month,filters).items() if value["closed"]}
    def has_records(self):
        return bool(database_manager.execute("SELECT 1 FROM operations LIMIT 1").fetchone() or database_manager.execute("SELECT 1 FROM paper_trades LIMIT 1").fetchone())
    def demo_allowed(self): return not self.has_records() or os.getenv("KRAKEN_DEMO_MODE","").lower() in ("1","true","yes")
    def load_demo(self, year, month):
        profile=profile_repository.get_active() or profile_repository.create(Profile(name="Demo Calendar", execution_mode="PAPER", risk_percent=1, max_open_trades=3, max_daily_loss=100))
        account=paper_trading_repository.account(profile.id); patterns=[(1,120,"TP3"),(2,-65,"SL"),(3,0,"CANCELLED"),(4,40,"TP1"),(5,-30,"SL"),(6,75,"TP2"),(7,15,"TP1"),(8,-20,"SL"),(9,0,"EXPIRED"),(10,90,"TP3"),(11,-45,"SL"),(12,25,"TP1"),(13,60,"TP2"),(14,-10,"SL"),(15,35,"TP1"),(15,18,"TP2")]
        for index,(day,net,result) in enumerate(patterns):
            key=f"demo-{year}-{month}-{index}"; opened=f"{year:04d}-{month:02d}-{day:02d} 09:30:00"; closed=f"{year:04d}-{month:02d}-{day:02d} 15:30:00"; costs=2.0
            paper_trading_repository.create_trade({"paper_account_id":account["id"],"operation_id":None,"signal_key":key,"profile_id":profile.id,"symbol":"EMASVOL10" if index%2==0 else "LIONX25","direction":"BUY" if index%2==0 else "SELL","status":"CLOSED","volume":0.1,"remaining_volume":0,"entry_price":100,"stop_loss":90,"take_profits":[],"gross_pl":net+costs,"spread_cost":1,"slippage_cost":.5,"commission_cost":.5,"net_pl":net,"initial_risk":20,"margin_estimate":10,"opened_at":opened,"closed_at":closed,"duration_seconds":21600,"updated_at":closed,"metadata":{"demo":True,"result":result,"source":"Telegram"}})
        return len(patterns)
    def delete_demo(self):
        cursor=database_manager.cursor(); cursor.execute("DELETE FROM paper_trades WHERE json_extract(metadata,'$.demo')=1"); database_manager.commit(); return cursor.rowcount
    def export_csv(self,rows,path):
        with Path(path).open("w",newline="",encoding="utf-8") as file:
            writer=csv.DictWriter(file,fieldnames=("date","id","symbol","direction","volume","gross","costs","net","result","mode","source","profile_id"),extrasaction="ignore"); writer.writeheader(); writer.writerows(rows)
    def export_excel(self,rows,path):
        # SpreadsheetML package without an external runtime dependency.
        headers=["date","id","symbol","direction","volume","gross","costs","net","result","mode","source","profile_id"]
        xml=lambda cells:"<row>"+"".join(f'<c t="inlineStr"><is><t>{str(c)}</t></is></c>' for c in cells)+"</row>"
        sheet="<?xml version='1.0' encoding='UTF-8'?><worksheet xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'><sheetData>"+xml(headers)+"".join(xml([r.get(h,"") for h in headers]) for r in rows)+"</sheetData></worksheet>"
        with ZipFile(path,"w",ZIP_DEFLATED) as z: z.writestr("[Content_Types].xml","<?xml version='1.0'?><Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'><Default Extension='rels' ContentType='application/vnd.openxmlformats-package.relationships+xml'/><Default Extension='xml' ContentType='application/xml'/><Override PartName='/xl/workbook.xml' ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml'/><Override PartName='/xl/worksheets/sheet1.xml' ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml'/></Types>"); z.writestr("_rels/.rels","<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'><Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument' Target='xl/workbook.xml'/></Relationships>"); z.writestr("xl/workbook.xml","<workbook xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main' xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'><sheets><sheet name='Trading Calendar' sheetId='1' r:id='rId1'/></sheets></workbook>"); z.writestr("xl/_rels/workbook.xml.rels","<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'><Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet' Target='worksheets/sheet1.xml'/></Relationships>"); z.writestr("xl/worksheets/sheet1.xml",sheet)
    def export_pdf(self,stats,path):
        text=f"Kraken Bot Enterprise | Trading Calendar | Net P/L {stats['net']} | Trades {stats['total']}"
        content=f"BT /F1 12 Tf 50 750 Td ({text}) Tj ET"; pdf=f"%PDF-1.4\n1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n2 0 obj<< /Type /Pages /Kids[3 0 R] /Count 1 >>endobj\n3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox[0 0 612 792] /Resources<< /Font<< /F1 4 0 R >> >> /Contents 5 0 R >>endobj\n4 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n5 0 obj<< /Length {len(content)} >>stream\n{content}\nendstream endobj\ntrailer<< /Root 1 0 R >>\n%%EOF"; Path(path).write_bytes(pdf.encode("latin-1","replace"))


trading_calendar_service=TradingCalendarService()
