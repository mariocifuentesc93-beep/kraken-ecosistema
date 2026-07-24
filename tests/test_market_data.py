import shutil
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from database.database_manager import database_manager
from models.profile import Profile
from models.signal import Signal
from repositories.market_price_event_repository import market_price_event_repository
from repositories.profile_repository import profile_repository
from services.market_data_service import market_data_service
from trading.execution_pipeline import execution_pipeline


class MarketDataTests(unittest.TestCase):
    def setUp(self):
        self.original = database_manager.database
        database_manager.close()
        self.directory = Path(tempfile.mkdtemp())
        database_manager.database = self.directory / "market.db"
        database_manager.initialize()
        self.profile = profile_repository.create(Profile(name="Market Simulation", execution_mode="SIMULATION"))

    def tearDown(self):
        database_manager.close()
        database_manager.database = self.original
        shutil.rmtree(self.directory)

    def test_valid_mt5_tick_and_stale_tick(self):
        info = SimpleNamespace(visible=True, trade_mode=1, digits=2)
        fresh_tick = SimpleNamespace(bid=100.0, ask=100.2, last=100.1, time=int(time.time()))
        with patch("services.market_data_service.mt5_connector.is_connected", return_value=True), \
             patch("services.market_data_service.mt5.symbol_info", return_value=info), \
             patch("services.market_data_service.mt5.symbol_info_tick", return_value=fresh_tick):
            quote = market_data_service.quote("EMASVOL10")
        self.assertEqual(quote["source"], "MT5")
        self.assertTrue(quote["fresh"])
        self.assertEqual(quote["spread"], 0.2)

        stale_tick = SimpleNamespace(bid=100.0, ask=100.2, last=100.1, time=int(time.time()) - 60)
        with patch("services.market_data_service.mt5_connector.is_connected", return_value=True), \
             patch("services.market_data_service.mt5.symbol_info", return_value=info), \
             patch("services.market_data_service.mt5.symbol_info_tick", return_value=stale_tick):
            self.assertFalse(market_data_service.quote("EMASVOL10", freshness_seconds=5)["fresh"])

    def test_unavailable_symbol_and_fallback_when_mt5_missing(self):
        self.assertFalse(market_data_service.quote("UNKNOWN", allow_fallback=False)["available"])
        with patch("services.market_data_service.mt5_connector.is_connected", return_value=False):
            quote = market_data_service.quote("EMASVOL10")
        self.assertEqual(quote["source"], "FALLBACK")
        self.assertTrue(quote["fresh"])

        stale = execution_pipeline.simulate_with_market_data(
            Signal(symbol="EMASVOL10", direction="BUY", entry=0, market_execution=True), self.profile,
            quote={"symbol": "EMASVOL10", "source": "TEST", "available": True,
                   "market_open": True, "fresh": False, "stale_reason": "Tick MT5 vencido."},
        )
        self.assertEqual(stale.status, "REJECTED")

    def test_market_fill_pending_activation_tp_and_sl(self):
        market_signal = Signal(symbol="EMASVOL10", direction="BUY", entry=100, stop_loss=90,
                               take_profits=[110], market_execution=True)
        filled = execution_pipeline.simulate_with_market_data(
            market_signal, self.profile,
            quote={"symbol": "EMASVOL10", "bid": 100, "ask": 100.1, "last": 100, "source": "TEST", "available": True, "market_open": True, "fresh": True},
        )
        self.assertEqual(filled.status, "SIMULATED")

        pending_signal = Signal(symbol="EMASVOL10", direction="BUY", entry=100, stop_loss=90,
                                take_profits=[110], market_execution=False)
        waiting = execution_pipeline.simulate_with_market_data(
            pending_signal, self.profile,
            quote={"symbol": "EMASVOL10", "bid": 101, "ask": 101.1, "last": 101, "source": "TEST", "available": True, "market_open": True, "fresh": True},
        )
        self.assertEqual(waiting.status, "QUEUED")
        activated = execution_pipeline.simulate_with_market_data(
            pending_signal, self.profile,
            quote={"symbol": "EMASVOL10", "bid": 99.8, "ask": 100, "last": 99.9, "source": "TEST", "available": True, "market_open": True, "fresh": True},
        )
        self.assertEqual(activated.status, "SIMULATED")
        self.assertEqual(execution_pipeline.evaluate_market_price(
            activated, pending_signal,
            {"symbol": "EMASVOL10", "bid": 111, "ask": 111.1, "last": 111, "source": "TEST"},
        ).status, "CLOSED")
        stopped = execution_pipeline.simulate_with_market_data(
            market_signal, self.profile,
            quote={"symbol": "EMASVOL10", "bid": 89, "ask": 89.1, "last": 89, "source": "TEST", "available": True, "market_open": True, "fresh": True},
        )
        self.assertEqual(stopped.status, "CLOSED")
        self.assertTrue(market_price_event_repository.get_all())

    def test_configured_symbol_validation_has_all_twenty_symbols(self):
        with patch("services.market_data_service.mt5_connector.is_connected", return_value=False):
            results = market_data_service.validate_configured_symbols()
        self.assertEqual(len(results), 20)
        self.assertTrue(all(not row["mt5_connected"] for row in results))


if __name__ == "__main__":
    unittest.main()
