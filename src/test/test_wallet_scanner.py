import os
import sys
import unittest
from unittest.mock import patch

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from services.wallet_scanner import WalletScanner


class WalletScannerTest(unittest.TestCase):
    def test_validates_evm_addresses(self):
        scanner = WalletScanner()
        self.assertTrue(scanner._is_valid_address("0x0000000000000000000000000000000000000001"))
        self.assertFalse(scanner._is_valid_address("0xnot-a-wallet"))
        self.assertFalse(scanner._is_valid_address("0000000000000000000000000000000000000001"))

    def test_scan_wallet_reads_public_polymarket_history(self):
        payloads = {
            "public-profile": {"proxyWallet": "0x0000000000000000000000000000000000000001"},
            "positions": [{"title": "Bitcoin above 100k?", "currentValue": "12.5"}],
            "closed-positions": [{"title": "Election winner?", "realizedPnl": "4.5"}],
            "activity": [],
            "trades": [
                {"title": "Bitcoin above 100k?", "side": "BUY", "cash": "10", "price": "0.42"},
                {"title": "Election winner?", "side": "SELL", "cash": "5", "price": "0.55"},
            ],
            "value": {"value": 12.5},
        }

        class Response:
            def __init__(self, data):
                self.data = data

            def raise_for_status(self):
                return None

            def json(self):
                return self.data

        def fake_get(url, params, proxies, timeout):
            endpoint = url.rstrip("/").split("/")[-1]
            return Response(payloads[endpoint])

        with patch("services.wallet_scanner.Config.GROQ_API_KEY", None), patch(
            "services.wallet_scanner.requests.get", side_effect=fake_get
        ):
            scanner = WalletScanner()
            result = scanner.scan_wallet("0x0000000000000000000000000000000000000001")

        self.assertTrue(result["valid"])
        self.assertEqual(result["stats"]["total_trades"], 2)
        self.assertEqual(result["stats"]["total_volume_usdc"], 15)
        self.assertEqual(result["stats"]["portfolio_value"], 12.5)
        self.assertEqual(result["stats"]["profit"], 4.5)
        self.assertIn(result["specialization"]["category"], {"crypto", "politique"})
        self.assertIn("Wallet Mirror", result["recommendation"])

    def test_format_report_includes_wallet_links_and_copyable_addresses(self):
        scanner = WalletScanner()
        result = {
            "valid": True,
            "address": "0x0000000000000000000000000000000000000001",
            "profile_wallet": "0x0000000000000000000000000000000000000002",
            "stats": {},
            "specialization": {},
            "recommendation": "OK",
            "pnl": 0,
        }

        report = scanner.format_report(result)

        self.assertIn("https://polymarket.com/profile/0x0000000000000000000000000000000000000001", report)
        self.assertIn("https://polyanalytics.com/address/0x0000000000000000000000000000000000000002", report)
        self.assertIn("https://polygonscan.com/address/0x0000000000000000000000000000000000000002", report)
        self.assertIn("ETH/POL: <code>0x0000000000000000000000000000000000000001</code>", report)
        self.assertIn("Proxy Polymarket/Polygon: <code>0x0000000000000000000000000000000000000002</code>", report)


if __name__ == "__main__":
    unittest.main()
