import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from services.smart_copy import (
    add_profile,
    apply_profile_to_amount,
    build_smart_copy_profile,
    format_profiles_dashboard,
    get_profile,
    save_profile,
)


class SmartCopyTest(unittest.TestCase):
    def test_build_profile_uses_requested_percentage_defaults(self):
        scan_result = {
            "stats": {"total_trades": 80, "total_volume_usdc": 5000, "win_rate": 0.6},
            "specialization": {"category": "crypto", "confidence": 0.7},
        }

        profile = build_smart_copy_profile(
            "alpha",
            "0x1111111111111111111111111111111111111111",
            250,
            scan_result,
            assigned_wallet="0x2222222222222222222222222222222222222222",
            assigned_wallet_label="manuel",
        )

        self.assertEqual(profile.mode, "Percentage")
        self.assertEqual(profile.trade_size_percent, 1.0)
        self.assertEqual(profile.single_trade_limit, 10.0)
        self.assertEqual(profile.price_range, "No Filter")
        self.assertEqual(profile.slippage, "Any Price")
        self.assertFalse(profile.auto_tp_sl)
        self.assertTrue(profile.simulation)
        self.assertEqual(profile.assigned_wallet, "0x2222222222222222222222222222222222222222")
        self.assertTrue(profile.wallet_type.startswith("specialist"))

    def test_apply_profile_caps_leader_amount(self):
        profile = {"trade_size_percent": 1.0, "single_trade_limit": 10.0, "portfolio_amount": 250}
        self.assertEqual(apply_profile_to_amount(100.0, profile), 10.0)
        self.assertEqual(apply_profile_to_amount(7.5, profile), 7.5)

    def test_save_and_get_profile_by_wallet(self):
        profile = build_smart_copy_profile(
            "alpha",
            "0x1111111111111111111111111111111111111111",
            250,
            None,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profiles.json"
            save_profile(profile, path=path)
            loaded = get_profile(profile.wallet.upper(), path=path)

        self.assertEqual(loaded["name"], "alpha")
        self.assertEqual(loaded["wallet"], profile.wallet)

    def test_add_profile_returns_and_saves_by_target_wallet(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profiles.json"
            profile = add_profile(
                name="alpha",
                wallet="0x1111111111111111111111111111111111111111",
                assigned_wallet="0x2222222222222222222222222222222222222222",
                portfolio_amount=250,
                path=path,
            )
            loaded = get_profile(profile["wallet"].upper(), path=path)

        self.assertEqual(profile["name"], "alpha")
        self.assertEqual(loaded["assigned_wallet"], "0x2222222222222222222222222222222222222222")

    def test_dashboard_shows_assigned_wallet_mapping(self):
        profiles = {
            "0x1111111111111111111111111111111111111111": {
                "name": "alpha",
                "wallet": "0x1111111111111111111111111111111111111111",
                "assigned_wallet": "0x2222222222222222222222222222222222222222",
                "portfolio_amount": 250,
                "single_trade_limit": 10,
                "wallet_type": "active",
            }
        }

        text = format_profiles_dashboard(profiles)

        self.assertIn("Simulation IA Wallet Mirror", text)
        self.assertIn("0x2222222222222222222222222222222222222222", text)
        self.assertIn("0x1111111111111111111111111111111111111111", text)


if __name__ == "__main__":
    unittest.main()
