from collections import Counter, defaultdict
from datetime import date, datetime

from services.trading_calendar_service import trading_calendar_service


class TradingAnalyticsService:
    def records(self, filters=None):
        filters=filters or {}; start=filters.get("start") or date(2000,1,1); end=filters.get("end") or date.today(); rows=[]; current=date(start.year,start.month,1)
        while current<=end:
            rows.extend(trading_calendar_service.records(current.year,current.month,filters)); current=date(current.year+(current.month==12),1 if current.month==12 else current.month+1,1)
        result=[]
        for row in rows:
            value=datetime.fromisoformat(str(row["date"]).replace("Z","+00:00")).date() if row.get("date") else None
            if value and start<=value<=end: result.append(row)
        return sorted(result,key=lambda row:row.get("date") or "")
    def metrics(self, filters=None):
        rows=self.records(filters); closed=[r for r in rows if r["status"]=="CLOSED"]; values=[float(r["net"] or 0) for r in closed]; wins=[v for v in values if v>0]; losses=[v for v in values if v<0]; gross_profit=sum(wins); gross_loss=sum(losses); cumulative=peak=drawdown=0; curve=[]; current_streak=best_streak=streak=0
        for row,value in zip(closed,values):
            cumulative+=value; peak=max(peak,cumulative); drawdown=max(drawdown,peak-cumulative); curve.append((row["date"],cumulative,peak-cumulative))
            sign=1 if value>0 else -1 if value<0 else 0
            streak=streak+sign if sign and (streak==0 or (streak>0)==(sign>0)) else sign
            current_streak=streak; best_streak=max(best_streak,streak)
        durations=[]
        for r in closed:
            try: durations.append((datetime.fromisoformat(str(r["closed_at"]))-datetime.fromisoformat(str(r["opened_at"]))).total_seconds())
            except (TypeError,ValueError): pass
        return {"net":round(sum(values),2),"gross_profit":round(gross_profit,2),"gross_loss":round(gross_loss,2),"win_rate":round(len(wins)/len(closed)*100,2) if closed else 0,"profit_factor":round(gross_profit/abs(gross_loss),2) if gross_loss else (gross_profit if gross_profit else 0),"expectancy":round(sum(values)/len(closed),2) if closed else 0,"total":len(closed),"average_trade":round(sum(values)/len(closed),2) if closed else 0,"maximum_drawdown":round(drawdown,2),"current_streak":current_streak,"best_streak":best_streak,"average_duration":round(sum(durations)/len(durations),2) if durations else 0,"curve":curve,"rows":rows,"closed":closed}
    def series(self, filters=None):
        data=self.metrics(filters); groups={"daily":defaultdict(float),"monthly":defaultdict(float),"symbol":defaultdict(float),"profile":defaultdict(float),"mode":defaultdict(float),"weekday":defaultdict(float),"hour":defaultdict(float),"result":defaultdict(int)}
        for r in data["closed"]:
            net=float(r["net"] or 0); value=str(r["date"]); parsed=datetime.fromisoformat(value.replace("Z","+00:00")); groups["daily"][parsed.date().isoformat()]+=net; groups["monthly"][value[:7]]+=net; groups["symbol"][r["symbol"]]+=net; groups["profile"][str(r["profile_id"] or "-")]+=net; groups["mode"][r["mode"]]+=net; groups["weekday"][parsed.strftime("%a")]+=net; groups["hour"][f"{parsed.hour:02d}:00"]+=net; groups["result"][r["result"]]+=1
        return {name:dict(values) for name,values in groups.items()}
    def tables(self,filters=None):
        series=self.series(filters); rows=self.metrics(filters)["closed"]
        def aggregate(key):
            result=defaultdict(lambda:{"trades":0,"net":0.0,"wins":0})
            for r in rows:
                item=result[str(r.get(key) or "-")]; item["trades"]+=1; item["net"]+=float(r["net"]); item["wins"]+=float(r["net"])>0
            return [{"name":name,**value,"win_rate":round(value["wins"]/value["trades"]*100,2)} for name,value in result.items()]
        days=sorted(series["daily"].items(),key=lambda item:item[1]); trades=sorted(rows,key=lambda row:float(row["net"] or 0))
        return {"symbol":aggregate("symbol"),"profile":aggregate("profile_id"),"mode":aggregate("mode"),"best_trades":trades[-5:][::-1],"worst_trades":trades[:5],"best_days":days[-5:][::-1],"worst_days":days[:5]}
    def export(self, filters, path, kind):
        rows=self.records(filters)
        if kind=="csv": return trading_calendar_service.export_csv(rows,path)
        if kind=="xlsx": return trading_calendar_service.export_excel(rows,path)
        return trading_calendar_service.export_pdf(self.metrics(filters),path)


trading_analytics_service=TradingAnalyticsService()
