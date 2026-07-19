import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from database.database_manager import database_manager
from models.profile import Profile
from repositories.paper_trading_repository import paper_trading_repository
from repositories.profile_repository import profile_repository
from services.trading_analytics_service import trading_analytics_service


class TradingAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.original=database_manager.database; database_manager.close(); self.directory=Path(tempfile.mkdtemp()); database_manager.database=self.directory/"analytics.db"; database_manager.initialize(); self.profile=profile_repository.create(Profile(name="Analytics")); self.account=paper_trading_repository.account(self.profile.id)
    def tearDown(self): database_manager.close(); database_manager.database=self.original; shutil.rmtree(self.directory)
    def add(self,day,net,symbol="EMASVOL10",mode="Paper"):
        return paper_trading_repository.create_trade({"paper_account_id":self.account["id"],"operation_id":None,"signal_key":f"analytics-{day}-{net}-{symbol}","profile_id":self.profile.id,"symbol":symbol,"direction":"BUY","status":"CLOSED","volume":1,"remaining_volume":0,"entry_price":100,"stop_loss":90,"take_profits":[],"gross_pl":net+2,"spread_cost":1,"slippage_cost":.5,"commission_cost":.5,"net_pl":net,"initial_risk":10,"margin_estimate":100,"opened_at":f"2024-03-{day:02d} 10:00:00","closed_at":f"2024-03-{day:02d} 11:00:00","duration_seconds":3600,"updated_at":f"2024-03-{day:02d} 11:00:00","metadata":{"result":"TP1" if net>0 else "SL"}})
    def filters(self,**extra): return {"start":date(2024,3,1),"end":date(2024,3,31),**extra}
    def test_metrics_drawdown_and_streaks(self):
        self.add(1,10); self.add(2,20); self.add(3,-15); self.add(4,-5)
        metrics=trading_analytics_service.metrics(self.filters())
        self.assertEqual(metrics["win_rate"],50); self.assertEqual(metrics["profit_factor"],1.5); self.assertEqual(metrics["expectancy"],2.5); self.assertEqual(metrics["maximum_drawdown"],20); self.assertEqual(metrics["best_streak"],2); self.assertEqual(metrics["current_streak"],-2)
    def test_symbol_mode_date_filters_empty_and_legacy(self):
        self.add(2,5,"EMASVOL10"); self.add(3,-2,"LIONX25")
        self.assertEqual(len(trading_analytics_service.records(self.filters(symbol="LIONX25"))),1)
        self.assertEqual(trading_analytics_service.metrics({"start":date(2024,4,1),"end":date(2024,4,30)})["total"],0)
        tables=trading_analytics_service.tables(self.filters()); self.assertEqual(len(tables["symbol"]),2)
        database_manager.execute("INSERT INTO operations(symbol, direction, status, profit, opened_at, closed_at) VALUES (?,?,?,?,?,?)",("LEGACY","BUY","CLOSED",4,"2024-03-04 10:00:00","2024-03-04 11:00:00")); database_manager.commit()
        self.assertTrue(any(row["symbol"]=="LEGACY" for row in trading_analytics_service.records(self.filters())))
    def test_exports(self):
        self.add(1,3); filters=self.filters(); csv_file=self.directory/"analytics.csv"; xlsx_file=self.directory/"analytics.xlsx"; pdf_file=self.directory/"analytics.pdf"
        for path,kind in ((csv_file,"csv"),(xlsx_file,"xlsx"),(pdf_file,"pdf")): trading_analytics_service.export(filters,path,kind)
        self.assertTrue(csv_file.exists() and xlsx_file.exists() and pdf_file.read_bytes().startswith(b"%PDF"))


if __name__=="__main__": unittest.main()
