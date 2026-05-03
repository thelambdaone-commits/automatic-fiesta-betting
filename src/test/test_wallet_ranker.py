import unittest
from unittest.mock import patch

from services.wallet_ranker import WalletRanker, WalletScore


class WalletRankerTest(unittest.TestCase):
    def test_rank_orders_wallets_by_total_pnl(self):
        data = [
            {"wallet": "0x1111111111111111111111111111111111111111", "pnl": 3.0, "volume": 1.0},
            {"wallet": "0x2222222222222222222222222222222222222222", "pnl": 9.0, "volume": 2.0},
        ]

        with patch("services.polymarket_analytics.get_top_wallets", return_value=data):
            scores = WalletRanker().rank()

        self.assertEqual(scores[0].wallet, "0x2222222222222222222222222222222222222222")
        self.assertEqual(scores[0].total_pnl, 9.0)
        self.assertEqual(scores[1].wallet, "0x1111111111111111111111111111111111111111")

    def test_format_scores_handles_empty(self):
        self.assertIn("Aucun wallet trouvé", WalletRanker.format_scores([]))

    def test_format_scores_is_readable_for_telegram(self):
        wallet = "0xaaaabbbbccccddddeeeeffff0000111122223333"
        scores = [
            WalletScore(
                wallet=wallet,
                total_pnl=12.34,
                realized_pnl=12.34,
                current_value=2.34,
                win_rate=0,
                total_trades=0,
                rank=1,
                username="alice",
            )
        ]

        text = WalletRanker.format_scores(scores)

        self.assertIn("Top 1 Wallets Polymarket", text)
        self.assertIn("alice", text)
        self.assertIn("PnL: `+12 USDC`", text)
        self.assertIn(wallet, text)

    def test_rank_by_theme_infers_theme_from_public_details(self):
        wallet = "0xaaaabbbbccccddddeeeeffff0000111122223333"
        data = [{"wallet": wallet, "pnl": 100.0, "volume": 500.0, "rank": 1}]
        details = {"positions": [{"title": "Will Bitcoin hit 100k?"}], "activity": [], "trades": []}

        with patch("services.polymarket_analytics.get_top_wallets", return_value=data):
            with patch("services.polymarket_analytics.get_wallet_details", return_value=details):
                scores = WalletRanker().rank_by_theme(limit=10)

        self.assertEqual(scores[0].theme, "crypto")
        text = WalletRanker.format_theme_scores(scores)
        self.assertIn("Top 1 Wallets Polymarket par thèmes", text)
        self.assertIn("🎯 crypto", text)
        self.assertIn(wallet, text)

    def test_selected_theme_scores_can_show_many_wallets_compactly(self):
        scores = [
            WalletScore(
                wallet=f"0x{i:040x}",
                total_pnl=1000 - i,
                realized_pnl=1000 - i,
                current_value=0,
                win_rate=0,
                total_trades=0,
                rank=i + 1,
                theme="sport",
            )
            for i in range(60)
        ]

        text = WalletRanker.format_selected_theme_scores(scores, "sport", display_limit=50)

        self.assertIn("Top 50 wallets", text)
        self.assertIn("0x0000000000000000000000000000000000000000", text)
        self.assertIn("0x0000000000000000000000000000000000000031", text)
        self.assertNotIn("0x0000000000000000000000000000000000000032", text)


if __name__ == "__main__":
    unittest.main()
