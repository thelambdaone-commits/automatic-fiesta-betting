import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.copy_trade import PolymarketTrader


class PolymarketTraderTest(unittest.TestCase):
    def test_normalize_side_accepts_polymarket_numeric_sides(self):
        self.assertEqual(PolymarketTrader.normalize_side(0), "BUY")
        self.assertEqual(PolymarketTrader.normalize_side("0"), "BUY")
        self.assertEqual(PolymarketTrader.normalize_side(1), "SELL")
        self.assertEqual(PolymarketTrader.normalize_side("1"), "SELL")

    def test_normalize_side_accepts_clob_string_sides(self):
        self.assertEqual(PolymarketTrader.normalize_side("BUY"), "BUY")
        self.assertEqual(PolymarketTrader.normalize_side("SELL"), "SELL")

    def test_normalize_side_rejects_unknown_side(self):
        with self.assertRaises(ValueError):
            PolymarketTrader.normalize_side("UNKNOWN")


class PolymarketTraderSmartCopyTest(unittest.IsolatedAsyncioTestCase):
    async def test_smart_copy_simulation_uses_profile_without_live_balance(self):
        trader = object.__new__(PolymarketTrader)
        trader.delay = 0
        trader.simulation = False
        trader.check_cash_balance = lambda: (_ for _ in ()).throw(AssertionError("live balance should not be read"))
        trader.send_telegram_notification = lambda message: None

        profile = {
            "name": "alpha",
            "portfolio_amount": 250.0,
            "trade_size_percent": 1.0,
            "single_trade_limit": 10.0,
            "simulation": True,
            "enabled": True,
        }

        with patch("services.copy_trade.get_profile", return_value=profile), patch(
            "services.copy_trade.jsonl_log_trade"
        ):
            result = await trader.execute_trade(
                {
                    "tokenId": "123456789",
                    "side": "BUY",
                    "makerAmount": 50,
                    "sourceWallet": "0x1111111111111111111111111111111111111111",
                }
            )

        self.assertEqual(result["status"], "simulated")
        self.assertEqual(result["amount"], 10.0)
        self.assertEqual(result["smart_profile"], "alpha")
