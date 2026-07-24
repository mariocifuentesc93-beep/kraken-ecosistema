import shutil
import tempfile
import unittest
from pathlib import Path

from database.database_manager import database_manager
from models.profile import Profile
from models.signal import Signal
from repositories.paper_trading_repository import paper_trading_repository
from repositories.profile_repository import profile_repository
from trading.paper_trading_engine import paper_trading_engine


class PaperTradingTests(unittest.TestCase):
    def setUp(self):
        self.original=database_manager.database; database_manager.close(); self.directory=Path(tempfile.mkdtemp()); database_manager.database=self.directory/"paper.db"; database_manager.initialize()
        self.profile=profile_repository.create(Profile(name="Paper",risk_percent=1,max_daily_loss=100,max_open_trades=3,min_lot=.01,max_lot=10))
        paper_trading_engine.configure(self.profile.id,starting_balance=10000,currency="USD",slippage=.1,commission=1,allow_fallback=True)
    def tearDown(self): database_manager.close(); database_manager.database=self.original; shutil.rmtree(self.directory)
    @staticmethod
    def quote(bid=100,ask=100.2): return {"symbol":"EMASVOL10","bid":bid,"ask":ask,"last":(bid+ask)/2,"source":"MT5","available":True,"fresh":True,"market_open":True}
    def signal(self,direction="BUY",market=True,entry=0): return Signal(id=None,chat_id=1,message_id=hash((direction,market,entry))%100000,symbol="EMASVOL10",direction=direction,entry=entry,market_execution=market,stop_loss=90 if direction=="BUY" else 110,take_profits=[110 if direction=="BUY" else 90,120 if direction=="BUY" else 80,130 if direction=="BUY" else 70])
    def test_buy_sell_fill_sizing_and_costs(self):
        buy=paper_trading_engine.execute(self.signal("BUY"),self.profile,quote=self.quote())
        sell=paper_trading_engine.execute(self.signal("SELL"),self.profile,quote=self.quote())
        self.assertAlmostEqual(buy["entry_price"],100.3); self.assertAlmostEqual(sell["entry_price"],99.9)
        self.assertGreater(buy["volume"],0); self.assertGreater(buy["initial_risk"],0); self.assertGreater(buy["spread_cost"],0); self.assertGreater(buy["slippage_cost"],0)
    def test_pending_activation_tp_partial_break_even_and_trailing(self):
        trade=paper_trading_engine.execute(self.signal(market=False,entry=100),self.profile,quote=self.quote(101,101.2)); self.assertEqual(trade["status"],"PENDING")
        self.assertEqual(paper_trading_engine.process_price(trade["id"],self.quote(99.8,100))["status"],"OPEN")
        trade=paper_trading_engine.process_price(trade["id"],self.quote(110,110.2)); self.assertTrue(trade["metadata"]["tp1_protected"]); self.assertEqual(trade["stop_loss"],110); self.assertEqual(trade["remaining_volume"],trade["volume"])
        trade=paper_trading_engine.process_price(trade["id"],self.quote(120,120.2)); self.assertTrue(trade["metadata"]["trailing"])
        trade=paper_trading_engine.process_price(trade["id"],self.quote(130,130.2)); self.assertEqual(trade["status"],"CLOSED")
    def test_sl_duplicate_balance_and_reset(self):
        trade=paper_trading_engine.execute(self.signal(),self.profile,quote=self.quote()); duplicate=paper_trading_engine.execute(self.signal(),self.profile,quote=self.quote()); self.assertIsNone(duplicate)
        closed=paper_trading_engine.process_price(trade["id"],self.quote(89,89.2)); self.assertEqual(closed["metadata"]["result"],"SL")
        summary=paper_trading_engine.summary(self.profile.id); self.assertNotEqual(summary["account"]["balance"],10000)
        reset=paper_trading_engine.reset(self.profile.id); self.assertEqual(reset["balance"],reset["starting_balance"]); self.assertEqual(paper_trading_engine.summary(self.profile.id)["closed"],0)
    def test_cancellation_expiration_and_fallback_policy(self):
        pending=paper_trading_engine.execute(self.signal(market=False,entry=100),self.profile,quote=self.quote(101,101.2)); self.assertEqual(paper_trading_engine.cancel(pending["id"])["status"],"CANCELLED")
        pending=paper_trading_engine.execute(self.signal(market=False,entry=99),self.profile,quote=self.quote(101,101.2)); self.assertEqual(paper_trading_engine.expire(pending["id"])["status"],"EXPIRED")
        paper_trading_engine.configure(self.profile.id,allow_fallback=False)
        fallback=dict(self.quote()); fallback["source"]="FALLBACK"
        rejected=paper_trading_engine.execute(self.signal("SELL",entry=0),self.profile,quote=fallback); self.assertEqual(rejected["status"],"REJECTED")


if __name__=="__main__": unittest.main()
