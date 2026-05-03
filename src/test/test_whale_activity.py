import os
import sys
import time
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from services.whale_activity import format_whale_activity_for_telegram


class WhaleActivityTest(unittest.TestCase):
    def test_format_includes_amount_market_and_links(self):
        wallet = "0x0000000000000000000000000000000000000001"
        text = format_whale_activity_for_telegram(
            [
                {
                    "wallet": wallet,
                    "side": "BUY",
                    "cash": "12.5",
                    "title": "Bitcoin above 100k?",
                    "slug": "bitcoin-above-100k",
                    "outcome": "YES",
                    "timestamp": int(time.time()),
                }
            ]
        )

        self.assertIn("$12.50", text)
        self.assertIn("Bitcoin above 100k?", text)
        self.assertIn(f"https://polymarket.com/profile/{wallet}", text)
        self.assertIn(f"https://polygonscan.com/address/{wallet}", text)
        self.assertIn("https://polymarket.com/event/bitcoin-above-100k", text)
        self.assertNotIn("Token: `N/A`", text)


if __name__ == "__main__":
    unittest.main()
