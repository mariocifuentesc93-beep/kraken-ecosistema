import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from database.database_manager import database_manager
from models.profile import Profile
from models.signal import Signal
from repositories.profile_repository import profile_repository
from services.trade_replay_service import trade_replay_service
from trading.execution_pipeline import execution_pipeline


class TradeReplayTests(unittest.TestCase):
    def setUp(self):
        self.original=database_manager.database; database_manager.close(); self.directory=Path(tempfile.mkdtemp()); database_manager.database=self.directory/"replay.db"; database_manager.initialize(); self.profile=profile_repository.create(Profile(name="Replay",execution_mode="SIMULATION")); self.signal=Signal(symbol="EMASVOL10",direction="BUY",entry=0,stop_loss=90,take_profits=[110,120,130],raw_message="BUY EMASVOL10")
        self.operation=execution_pipeline.simulate_with_market_data(self.signal,self.profile,quote={"symbol":"EMASVOL10","bid":100,"ask":100.2,"last":100.1,"source":"TEST","available":True,"fresh":True,"market_open":True})
    def tearDown(self): database_manager.close(); database_manager.database=self.original; shutil.rmtree(self.directory)
    def test_session_chronology_filter_state_jump_and_scrubbing(self):
        session=trade_replay_service.session(date.today(),{"profile":self.profile.id,"symbol":"EMASVOL10","mode":"Simulation"})
        self.assertGreater(len(session["events"]),3); self.assertEqual(session["events"],sorted(session["events"],key=lambda event:event.get("time") or "")); self.assertGreaterEqual(trade_replay_service.state_index(session["events"],"SIMULATED"),0)
        self.assertEqual(trade_replay_service.session(date.today(),{"symbol":"OTHER"})["events"],[])
    def test_exports_and_no_order_api(self):
        session=trade_replay_service.session(date.today()); json_file=self.directory/"replay.json"; pdf_file=self.directory/"replay.pdf"; trade_replay_service.export_json(session,json_file); trade_replay_service.export_pdf(session,pdf_file)
        self.assertTrue(json_file.exists() and pdf_file.read_bytes().startswith(b"%PDF"))
        self.assertNotIn("order_send", Path("trading/paper_trading_engine.py").read_text(encoding="utf-8"))


if __name__=="__main__": unittest.main()
