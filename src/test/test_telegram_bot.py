import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import requests

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "src"))

from services.telegram_bot import TelegramControlBot
from services.wallet_ranker import THEME_RANK_LIMIT, WalletScore


class TelegramControlBotTest(unittest.TestCase):
    def test_keyboard_contains_core_actions(self):
        keyboard = TelegramControlBot.keyboard()
        buttons = [
            button["callback_data"]
            for row in keyboard["inline_keyboard"]
            for button in row
        ]
        self.assertIn("top_wallets_menu", buttons)
        self.assertIn("wallet_mirror", buttons)
        self.assertIn("scan_wallet_prompt", buttons)
        self.assertIn("ia_analysis", buttons)
        self.assertIn("whale_activity", buttons)
        self.assertIn("my_wallet", buttons)
        self.assertIn("manual_trade", buttons)
        self.assertIn("help", buttons)
        self.assertNotIn("risk_menu", buttons)

    def test_market_search_keyboard_matches_expected_filters(self):
        keyboard = TelegramControlBot.market_search_keyboard()
        labels = [
            button["text"]
            for row in keyboard["inline_keyboard"]
            for button in row
        ]
        for label in [
            "🏛️ Politics",
            "🥇 Sports",
            "🌚 Crypto",
            "🦅 Trump",
            "💹 Finance",
            "🌍 Geopolitics",
            "📊 Volume",
            "🔥 Trending",
            "🏠 Accueil",
        ]:
            self.assertIn(label, labels)

    def test_autopilot_keyboard_matches_expected_buttons(self):
        keyboard = TelegramControlBot.autopilot_keyboard()
        labels = [
            button["text"]
            for row in keyboard["inline_keyboard"]
            for button in row
        ]
        self.assertIn("📊 Activity", labels)
        self.assertIn("➕ New", labels)
        self.assertIn("🔄 Refresh", labels)

    def test_market_search_action_text(self):
        bot = object.__new__(TelegramControlBot)
        text = bot.handle_action("market_search")
        self.assertIn("🔍 Market Search — Choose a filter", text)
        self.assertIn("/search bitcoin", text)

    def test_autopilot_action_text(self):
        bot = object.__new__(TelegramControlBot)
        text = bot.handle_action("autopilot")
        self.assertIn("🦞 AutoPilot", text)
        self.assertIn("Aucune stratégie active", text)

    def test_help_action_text(self):
        bot = object.__new__(TelegramControlBot)
        text = bot.handle_action("help")

        self.assertIn("🩺 Help", text)
        self.assertIn("/smartcopy", text)
        self.assertIn("Mes paires", text)

    def test_scan_wallet_and_wallet_search_buttons_exist_with_text(self):
        keyboard = TelegramControlBot.keyboard()
        labels = [
            button["text"]
            for row in keyboard["inline_keyboard"]
            for button in row
        ]
        self.assertIn("🔍 Scanner Wallet", labels)
        self.assertIn("🧬 Mon Wallet", labels)

        bot = object.__new__(TelegramControlBot)
        self.assertIn("Scan Wallet", bot.handle_action("scan_wallet"))
        self.assertIn("/scan <wallet>", bot.handle_action("scan_wallet"))
        self.assertIn("Wallet Search", bot.handle_action("wallet_search"))

        # Verify scan_wallet and wallet_search return different keyboards
        bot._rank_scores = []
        bot._rank_page = 0
        scan_kb = bot.keyboard_for_action("scan_wallet")
        search_kb = bot.keyboard_for_action("wallet_search")
        self.assertNotEqual(scan_kb, search_kb)

    def test_market_filter_uses_gamma_results(self):
        bot = object.__new__(TelegramControlBot)
        bot.request_timeout = 20

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {"markets": [{"title": "Will Bitcoin hit 100k?", "slug": "bitcoin-100k", "volume": 1234}]}

        with patch("services.telegram_bot.requests.get", return_value=Response()):
            text = bot.handle_action("market_filter_crypto")

        self.assertIn("Market Search — Crypto", text)
        self.assertIn("Will Bitcoin hit 100k?", text)

    def test_handle_action_top1_uses_top1_report(self):
        bot = object.__new__(TelegramControlBot)
        wallet = "0x1111111111111111111111111111111111111111"
        with patch("services.polymarket_analytics.get_top_1_percent", return_value=[{"wallet": wallet, "pnl": 100000, "volume": 200000}]):
            text = bot.handle_action("top1")
        self.assertIn("Top Wallets Polymarket", text)
        self.assertIn(wallet, text)

    def test_groq_action_returns_readable_error_when_api_fails(self):
        bot = object.__new__(TelegramControlBot)
        with patch("services.telegram_bot.WalletRanker") as ranker, patch("services.telegram_bot.GroqAdvisor") as advisor:
            ranker.return_value.rank.return_value = [object()]
            advisor.return_value.analyze_wallets.side_effect = RuntimeError("Invalid API Key")
            text = bot.handle_action("groq_analyze")

        self.assertIn("Analyse Groq indisponible", text)

    def test_send_message_retries_without_markdown_on_telegram_400(self):
        bot = object.__new__(TelegramControlBot)
        bot.chat_ids = ["1"]
        response = requests.Response()
        response.status_code = 400
        error = requests.HTTPError(response=response)

        with patch.object(bot, "api", side_effect=[error, {"ok": True}]) as api:
            result = bot.send_message("Usage: `/scan <wallet>`")

        self.assertEqual(result, [{"ok": True}])
        self.assertEqual(api.call_count, 2)
        self.assertNotIn("parse_mode", api.call_args_list[1].args[1])

    def test_truncate_caps_long_messages(self):
        text = TelegramControlBot.truncate("x" * 5000, limit=100)
        self.assertLessEqual(len(text), 100)
        self.assertIn("output truncated", text)

    def test_top_wallets_keyboard_has_context_actions(self):
        keyboard = TelegramControlBot.top_wallets_keyboard()
        buttons = [
            button["callback_data"]
            for row in keyboard["inline_keyboard"]
            for button in row
        ]
        self.assertIn("rank_prev", buttons)
        self.assertIn("rank_next", buttons)
        self.assertIn("rank_wallets", buttons)
        self.assertIn("rank_wallets_themes", buttons)
        self.assertIn("groq_analyze", buttons)
        self.assertIn("menu", buttons)

    def test_top_wallets_themes_action_formats_theme_report(self):
        bot = object.__new__(TelegramControlBot)
        with patch("services.telegram_bot.WalletRanker") as ranker:
            instance = ranker.return_value
            instance.rank_by_theme.return_value = [object()]
            ranker.format_theme_menu.return_value = "theme menu"
            text = bot.handle_action("rank_wallets_themes")

        self.assertEqual(text, "theme menu")
        instance.rank_by_theme.assert_called_once_with(limit=THEME_RANK_LIMIT)

    def test_top_wallets_themes_keyboard_has_theme_choice_buttons(self):
        bot = object.__new__(TelegramControlBot)
        bot._rank_scores = [
            WalletScore(
                wallet="0x1111111111111111111111111111111111111111",
                total_pnl=100,
                realized_pnl=100,
                current_value=200,
                win_rate=0,
                total_trades=0,
                rank=1,
                theme="crypto",
            )
        ]

        keyboard = bot.keyboard_for_action("rank_wallets_themes")
        labels = [button["text"] for row in keyboard["inline_keyboard"] for button in row]
        callbacks = [button["callback_data"] for row in keyboard["inline_keyboard"] for button in row]

        self.assertIn("🌚 Crypto", labels)
        self.assertIn("rank_theme_crypto", callbacks)
        self.assertIn("rank_wallets_themes", callbacks)
        self.assertIn("menu", callbacks)

    def test_rank_theme_action_filters_selected_theme(self):
        bot = object.__new__(TelegramControlBot)
        bot._rank_scores = [
            WalletScore(
                wallet="0x1111111111111111111111111111111111111111",
                total_pnl=100,
                realized_pnl=100,
                current_value=200,
                win_rate=0,
                total_trades=0,
                rank=1,
                theme="crypto",
            ),
            WalletScore(
                wallet="0x2222222222222222222222222222222222222222",
                total_pnl=90,
                realized_pnl=90,
                current_value=180,
                win_rate=0,
                total_trades=0,
                rank=2,
                theme="sport",
            ),
        ]

        text = bot.handle_action("rank_theme_crypto")
        keyboard = bot.keyboard_for_action("rank_theme_crypto")
        labels = [button["text"] for row in keyboard["inline_keyboard"] for button in row]

        self.assertIn("Crypto", text)
        self.assertIn("0x1111111111111111111111111111111111111111", text)
        self.assertNotIn("0x2222222222222222222222222222222222222222", text)
        self.assertIn("🔍 #1 0x111111...111111", labels)
        self.assertIn("⬅️ Thèmes", labels)

    def test_top_wallets_themes_keyboard_exposes_top_50_all_themes(self):
        bot = object.__new__(TelegramControlBot)
        bot._rank_scores = []

        keyboard = bot.keyboard_for_action("rank_wallets_themes")
        labels = [button["text"] for row in keyboard["inline_keyboard"] for button in row]
        callbacks = [button["callback_data"] for row in keyboard["inline_keyboard"] for button in row]

        self.assertIn("🏆 Top 50 all thèmes", labels)
        self.assertIn("rank_theme_top10_all", callbacks)

    def test_smart_copy_prompt_action(self):
        bot = object.__new__(TelegramControlBot)
        text = bot.handle_action("smart_copy_prompt")

        self.assertIn("Smart Copy simulé IA", text)
        self.assertIn("/smartcopy <nom> <wallet_cible> <portfolio_usdc> [mon_wallet]", text)
        self.assertIn("Trade Size: 100% of leader's amount", text)

    def test_simulation_text_lists_saved_smart_copy_mapping(self):
        bot = object.__new__(TelegramControlBot)
        profiles = {
            "0x1111111111111111111111111111111111111111": {
                "name": "alpha",
                "wallet": "0x1111111111111111111111111111111111111111",
                "assigned_wallet": "0x2222222222222222222222222222222222222222",
                "portfolio_amount": 250,
            }
        }
        with patch("services.smart_copy.load_profiles", return_value=profiles):
            text = bot.handle_action("simulate_trade")

        self.assertIn("Associations retenues", text)
        self.assertIn("0x2222222222222222222222222222222222222222", text)
        self.assertIn("0x1111111111111111111111111111111111111111", text)

    def test_copy_pairs_lists_smart_and_standard_pairs(self):
        bot = object.__new__(TelegramControlBot)
        smart_target = "0x1111111111111111111111111111111111111111"
        standard_target = "0x3333333333333333333333333333333333333333"
        assigned = "0x2222222222222222222222222222222222222222"
        profiles = {
            smart_target: {
                "name": "alpha",
                "wallet": smart_target,
                "assigned_wallet": assigned,
                "portfolio_amount": 250,
                "single_trade_limit": 10,
                "wallet_type": "specialist:crypto",
            }
        }

        with patch("services.telegram_bot.Config.TARGET_WALLETS", [smart_target, standard_target]), patch(
            "services.smart_copy.load_profiles",
            return_value=profiles,
        ), patch.object(TelegramControlBot, "_configured_signer_wallet", return_value="0xSigner"):
            text = bot.handle_action("copy_pairs")
            keyboard = bot.keyboard_for_action("copy_pairs")

        callbacks = [
            button["callback_data"]
            for row in keyboard["inline_keyboard"]
            for button in row
        ]
        self.assertIn("Mes paires de copytrading", text)
        self.assertIn(assigned, text)
        self.assertIn(smart_target, text)
        self.assertIn("specialist:crypto", text)
        self.assertIn("Wallet Mirror standard", text)
        self.assertIn(standard_target, text)
        self.assertIn("copy_pairs", callbacks)

    def test_risk_menu_is_per_followed_wallet(self):
        bot = object.__new__(TelegramControlBot)
        wallet = "0x1111111111111111111111111111111111111111"

        with patch("services.telegram_bot.Config.TARGET_WALLETS", [wallet]), patch(
            "services.smart_copy.get_profile",
            return_value=None,
        ):
            text = bot.handle_action("risk_menu")
            detail = bot.handle_action(f"risk_wallet_{wallet}")
            keyboard = bot.keyboard_for_action("risk_menu")

        callbacks = [
            button["callback_data"]
            for row in keyboard["inline_keyboard"]
            for button in row
        ]
        self.assertIn("Gestion des Risques par Wallet", text)
        self.assertIn(wallet, text)
        self.assertIn("Standard Wallet Mirror", text)
        self.assertIn("Mon wallet attribué", text)
        self.assertIn(f"risk_wallet_{wallet}", callbacks)
        self.assertIn("Profil Risque Wallet", detail)
        self.assertIn("Pas de copie all-in", detail)

    def test_risk_profile_uses_smart_copy_profile_for_target_wallet(self):
        bot = object.__new__(TelegramControlBot)
        wallet = "0x1111111111111111111111111111111111111111"
        assigned = "0x2222222222222222222222222222222222222222"
        profile = {
            "name": "alpha",
            "wallet": wallet,
            "assigned_wallet": assigned,
            "portfolio_amount": 250,
            "wallet_type": "specialist:sport",
            "single_trade_limit": 10,
            "slippage": "Any Price",
        }

        with patch("services.telegram_bot.Config.TARGET_WALLETS", [wallet]), patch(
            "services.smart_copy.get_profile",
            return_value=profile,
        ):
            text = bot.handle_action(f"risk_wallet_{wallet}")

        self.assertIn("alpha", text)
        self.assertIn(assigned, text)
        self.assertIn("specialist:sport", text)
        self.assertIn("$10.00", text)
        self.assertIn("ON ✅ forcée", text)
        self.assertIn("Trade Size 100% du leader", text)


if __name__ == "__main__":
    unittest.main()
