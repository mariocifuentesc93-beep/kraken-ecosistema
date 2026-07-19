import calendar
import csv
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from database.database_manager import database_manager


class TradingCalendarService:
    """Read-only calendar projections over SQLite operation and paper-trade records."""
    def records(self, year, month, filters=None):
        filters = filters or {}; first=f"{year:04d}-{month:02d}-01"; last=f"{year + (month==12):04d}-{(month%12)+1:02d}-01"
        operations=database_manager.execute("""SELECT o.*, COALESCE(s.source,'Telegram') source,
            COALESCE((SELECT execution_mode FROM operation_events e WHERE e.operation_id=o.id ORDER BY e.id DESC LIMIT 1),'Simulation') mode
            FROM operations o LEFT JOIN signals s ON s.id=o.signal_id WHERE COALESCE(o.closed_at,o.opened_at)>=? AND COALESCE(o.closed_at,o.opened_at)<?""",(first,last)).fetchall()
        papers=database_manager.execute("SELECT * FROM paper_trades WHERE COALESCE(closed_at,opened_at)>=? AND COALESCE(closed_at,opened_at)<?",(first,last)).fetchall()
        rows=[]
        for row in operations:
            r=dict(row); rows.append({"id":f"O{r['id']}","date":r.get("closed_at") or r.get("opened_at"),"profile_id":r.get("profile_id"),"account_id":r.get("mt5_account_id"),"symbol":r.get("symbol"),"direction":r.get("direction"),"entry":r.get("entry_price"),"exit":r.get("exit_price"),"volume":r.get("volume"),"risk":0,"gross":r.get("profit",0) or 0,"costs":0,"net":r.get("profit",0) or 0,"result":r.get("result") or r.get("status"),"status":r.get("status"),"mode":str(r.get("mode") or "Simulation").title(),"source":r.get("source") or "Telegram","opened_at":r.get("opened_at"),"closed_at":r.get("closed_at")})
        for row in papers:
            r=dict(row); rows.append({"id":f"P{r['id']}","date":r.get("closed_at") or r.get("opened_at"),"profile_id":r.get("profile_id"),"account_id":None,"symbol":r.get("symbol"),"direction":r.get("direction"),"entry":r.get("entry_price"),"exit":None,"volume":r.get("volume"),"risk":r.get("initial_risk",0),"gross":r.get("gross_pl",0),"costs":sum(r.get(k,0) or 0 for k in ("spread_cost","slippage_cost","commission_cost")),"net":r.get("net_pl",0),"result":r.get("status"),"status":r.get("status"),"mode":"Paper","source":"Telegram","opened_at":r.get("opened_at"),"closed_at":r.get("closed_at")})
        return [r for r in rows if self._matches(r,filters)]
    @staticmethod
    def _matches(row,f):
        return (not f.get("profile") or str(row["profile_id"])==str(f["profile"])) and (not f.get("symbol") or row["symbol"]==f["symbol"]) and (not f.get("account") or str(row["account_id"])==str(f["account"])) and (not f.get("mode") or f["mode"]=="All" or row["mode"].lower()==f["mode"].lower()) and (not f.get("source") or f["source"]=="All" or row["source"].lower()==f["source"].lower())
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
        text=f"Kraken Bot Trading Calendar | Net P/L {stats['net']} | Trades {stats['total']}"
        content=f"BT /F1 12 Tf 50 750 Td ({text}) Tj ET"; pdf=f"%PDF-1.4\n1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n2 0 obj<< /Type /Pages /Kids[3 0 R] /Count 1 >>endobj\n3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox[0 0 612 792] /Resources<< /Font<< /F1 4 0 R >> >> /Contents 5 0 R >>endobj\n4 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n5 0 obj<< /Length {len(content)} >>stream\n{content}\nendstream endobj\ntrailer<< /Root 1 0 R >>\n%%EOF"; Path(path).write_bytes(pdf.encode("latin-1","replace"))


trading_calendar_service=TradingCalendarService()
