import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from services.monitor import WalletMonitor


class WalletMonitorUnitTest(unittest.IsolatedAsyncioTestCase):
    def test_configured_wallets_supports_multiple_prod_targets(self):
        missing_targets = Path(tempfile.gettempdir()) / "missing-wallets-for-monitor-test.json"
        with patch("services.monitor.Config.TARGET_WALLETS", ["0x1", "0x2", "0x1"]), patch(
            "services.monitor.Config.TARGET_WALLET", "0x3"
        ), patch("services.monitor.Config.TARGETS_FILE", missing_targets), patch(
            "services.monitor.Config.CONFIG_DIR", missing_targets.parent
        ):
            self.assertEqual(WalletMonitor._configured_wallets("prod"), ["0x1", "0x2"])

    def test_configured_wallets_includes_copy_targets_for_simulation(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            targets_dir = config_dir / "targets"
            targets_dir.mkdir()
            targets_file = targets_dir / "wallets.json"
            targets_file.write_text(
                json.dumps(
                    {
                        "wallet_mirror_wallets": ["0xTarget", "0xSmart"],
                        "test_wallet": "0xtest",
                    }
                ),
                encoding="utf-8",
            )
            (targets_dir / "smart_copy_profiles.json").write_text(
                json.dumps(
                    {
                        "profiles": {
                            "0xSmart": {"wallet": "0xSmart", "enabled": True},
                            "0xDisabled": {"wallet": "0xDisabled", "enabled": False},
                        }
                    }
                ),
                encoding="utf-8",
            )

            with patch("services.monitor.Config.TEST_WALLET", "0xtest"), patch(
                "services.monitor.Config.TARGET_WALLETS", []
            ), patch("services.monitor.Config.TARGETS_FILE", targets_file), patch(
                "services.monitor.Config.CONFIG_DIR", config_dir
            ):
                self.assertEqual(WalletMonitor._configured_wallets("test"), ["0xtest", "0xTarget", "0xSmart"])

    async def test_resolve_transaction_accepts_full_transaction_object(self):
        monitor = object.__new__(WalletMonitor)
        tx = {"hash": "0xabc", "input": "0x"}
        self.assertEqual(await monitor._resolve_transaction(tx), tx)

    async def test_resolve_transaction_fetches_hash_payload(self):
        monitor = object.__new__(WalletMonitor)
        monitor.web3 = Mock()
        monitor.web3.eth.get_transaction.return_value = {"hash": "0xabc", "input": "0x"}

        async def fake_to_thread(func):
            return func()

        with patch("services.monitor.asyncio.to_thread", side_effect=fake_to_thread):
            tx = await monitor._resolve_transaction("0xabc")

        self.assertEqual(tx["hash"], "0xabc")
        monitor.web3.eth.get_transaction.assert_called_once_with("0xabc")


if __name__ == "__main__":
    unittest.main()
