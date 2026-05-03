import os
import sys
import unittest
from unittest.mock import patch

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from services.polymarket_analytics import fetch_top_wallets, get_top_1_percent, is_evm_address


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class PolymarketAnalyticsTest(unittest.TestCase):
    def test_fetch_top_wallets_paginates_leaderboard(self):
        calls = []

        def fake_get(_url, params=None, **_kwargs):
            calls.append(params)
            offset = params["offset"]
            payload = [
                {
                    "rank": str(offset + index + 1),
                    "proxyWallet": f"0x{offset + index + 1:040x}",
                    "userName": f"wallet-{offset + index + 1}",
                    "pnl": 1000 - offset - index,
                    "vol": 10000,
                }
                for index in range(params["limit"])
            ]
            return FakeResponse(payload)

        with patch("services.polymarket_analytics.requests.get", side_effect=fake_get):
            wallets = fetch_top_wallets(limit=120, window="all")

        self.assertEqual(len(wallets), 120)
        self.assertEqual([call["limit"] for call in calls], [50, 50, 20])
        self.assertEqual([call["offset"] for call in calls], [0, 50, 100])
        self.assertEqual({call["timePeriod"] for call in calls}, {"ALL"})

    def test_top_wallets_are_valid_evm_addresses(self):
        wallets = get_top_1_percent(min_pnl=100000)
        self.assertGreaterEqual(len(wallets), 1)
        for wallet in wallets:
            self.assertTrue(is_evm_address(wallet["wallet"]), wallet["wallet"])

    def test_top_wallets_are_sorted_by_pnl_desc(self):
        wallets = get_top_1_percent(min_pnl=0)
        pnls = [wallet["pnl"] for wallet in wallets]
        self.assertEqual(pnls, sorted(pnls, reverse=True))


if __name__ == "__main__":
    unittest.main()
