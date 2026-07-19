import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from database.database_manager import database_manager
from models.profile import Profile
from repositories.paper_trading_repository import paper_trading_repository
from repositories.profile_repository import profile_repository
from services.trading_calendar_service import trading_calendar_service


class TradingCalendarTests(unittest.TestCase):
    def setUp(self):
        self.original=database_manager.database; database_manager.close(); self.directory=Path(tempfile.mkdtemp()); database_manager.database=self.directory/"calendar.db"; database_manager.initialize(); self.profile=profile_repository.create(Profile(name="Calendar")); self.account=paper_trading_repository.account(self.profile.id)
    def tearDown(self): database_manager.close(); database_manager.database=self.original; shutil.rmtree(self.directory)
    def trade(self,day,net,symbol="EMASVOL10"):
        return paper_trading_repository.create_trade({"paper_account_id":self.account["id"],"operation_id":None,"signal_key":f"{day}-{net}-{symbol}","profile_id":self.profile.id,"symbol":symbol,"direction":"BUY","status":"CLOSED","volume":1,"remaining_volume":0,"entry_price":100,"stop_loss":90,"take_profits":[],"gross_pl":net+2,"spread_cost":1,"slippage_cost":.5,"commission_cost":.5,"net_pl":net,"initial_risk":10,"margin_estimate":100,"opened_at":f"2024-02-{day:02d} 10:00:00","closed_at":f"2024-02-{day:02d} 11:00:00","duration_seconds":3600,"updated_at":f"2024-02-{day:02d} 11:00:00","metadata":{}})
    def test_profitable_losing_multiple_and_statistics(self):
        self.trade(2,10); self.trade(2,5); self.trade(3,-8,"LIONX25")
        daily=trading_calendar_service.daily(2024,2); self.assertEqual(daily[2]["net"],15); self.assertEqual(daily[2]["closed"],2); self.assertEqual(daily[3]["net"],-8)
        stats=trading_calendar_service.statistics(2024,2); self.assertEqual(stats["total"],3); self.assertEqual(stats["wins"],2); self.assertEqual(stats["losses"],1); self.assertEqual(stats["best_day"],15)
    def test_leap_empty_filters_details_and_navigation_data(self):
        self.assertEqual(len(trading_calendar_service.daily(2024,2)),29); self.assertEqual(trading_calendar_service.statistics(2024,2)["total"],0)
        self.trade(10,4,"EMASVOL10"); self.trade(11,4,"LIONX25")
        rows=trading_calendar_service.records(2024,2,{"symbol":"LIONX25"}); self.assertEqual(len(rows),1); self.assertEqual(trading_calendar_service.daily(2024,2)[11]["trades"][0]["symbol"],"LIONX25")
        self.assertIn((2,10),trading_calendar_service.annual_heatmap(2024))
    def test_exports_and_schema_migration_compatibility(self):
        self.trade(1,2); rows=trading_calendar_service.records(2024,2); csv_file=self.directory/"report.csv"; excel_file=self.directory/"report.xlsx"; pdf_file=self.directory/"report.pdf"
        trading_calendar_service.export_csv(rows,csv_file); trading_calendar_service.export_excel(rows,excel_file); trading_calendar_service.export_pdf(trading_calendar_service.statistics(2024,2),pdf_file)
        self.assertTrue(csv_file.exists() and excel_file.exists() and pdf_file.read_bytes().startswith(b"%PDF"))
        database_manager.close(); legacy=self.directory/"legacy.db"; sqlite3.connect(legacy).close(); database_manager.database=legacy; database_manager.initialize(); self.assertTrue(database_manager.table_exists("paper_trades"))

    def test_deterministic_demo_data_and_safe_deletion(self):
        self.assertTrue(trading_calendar_service.demo_allowed())
        self.assertEqual(trading_calendar_service.load_demo(2024, 2), 16)
        daily=trading_calendar_service.daily(2024, 2)
        self.assertGreaterEqual(sum(bool(day["trades"]) for day in daily.values()), 15)
        results={trade["result"] for day in daily.values() for trade in day["trades"]}
        self.assertTrue({"TP1","TP2","TP3","SL"}.issubset(results))
        self.assertEqual(daily[15]["closed"],2)
        manual=self.trade(20, 7, "MANUAL")
        self.assertEqual(trading_calendar_service.delete_demo(),16)
        self.assertEqual(len(trading_calendar_service.records(2024,2,{"symbol":"MANUAL"})),1)


if __name__=="__main__": unittest.main()
