"""Backward-compatible imports for the modular Telegram bot."""

import requests

from core.config import Config
from services.groq_advisor import GroqAdvisor
from services.telegram.bot import TelegramControlBot as _ModularTelegramControlBot
from services.wallet_ranker import WalletRanker


class TelegramControlBot(_ModularTelegramControlBot):
    """Compatibility wrapper for older tests and scripts."""

    @staticmethod
    def keyboard():
        return {
            "inline_keyboard": [
                [{"text": "🏆 Top Wallets", "callback_data": "top_wallets_menu"}, {"text": "🪞 Wallet Mirror", "callback_data": "wallet_mirror"}],
                [{"text": "🔍 Scanner Wallet", "callback_data": "scan_wallet_prompt"}, {"text": "🧬 Mon Wallet", "callback_data": "my_wallet"}],
                [{"text": "🤖 IA", "callback_data": "ia_analysis"}, {"text": "🐋 Whale", "callback_data": "whale_activity"}],
                [{"text": "💸 Manuel", "callback_data": "manual_trade"}, {"text": "🩺 Help", "callback_data": "help"}],
            ]
        }

    @staticmethod
    def market_search_keyboard():
        return {
            "inline_keyboard": [
                [{"text": "🏛️ Politics", "callback_data": "market_filter_politics"}, {"text": "🥇 Sports", "callback_data": "market_filter_sports"}],
                [{"text": "🌚 Crypto", "callback_data": "market_filter_crypto"}, {"text": "🦅 Trump", "callback_data": "market_filter_trump"}],
                [{"text": "💹 Finance", "callback_data": "market_filter_finance"}, {"text": "🌍 Geopolitics", "callback_data": "market_filter_geopolitics"}],
                [{"text": "📊 Volume", "callback_data": "market_filter_volume"}, {"text": "🔥 Trending", "callback_data": "market_filter_trending"}],
                [{"text": "🏠 Accueil", "callback_data": "menu"}],
            ]
        }

    @staticmethod
    def autopilot_keyboard():
        return {
            "inline_keyboard": [
                [{"text": "📊 Activity", "callback_data": "activity"}, {"text": "➕ New", "callback_data": "smart_copy_prompt"}],
                [{"text": "🔄 Refresh", "callback_data": "autopilot"}, {"text": "🏠 Accueil", "callback_data": "menu"}],
            ]
        }

    def handle_action(self, action: str) -> str:
        if action == "market_search":
            return "🔍 Market Search — Choose a filter\n\nUse /search bitcoin to search markets."
        if action.startswith("market_filter_"):
            label = action.replace("market_filter_", "").replace("_", " ").title()
            query = label.lower()
            response = requests.get(
                f"{Config.GAMMA_API_HOST.rstrip('/')}/markets",
                params={"search": query, "limit": 5},
                timeout=getattr(self, "request_timeout", 20),
            )
            response.raise_for_status()
            payload = response.json()
            markets = payload.get("markets", payload if isinstance(payload, list) else [])
            lines = [f"Market Search — {label}", ""]
            for market in markets[:5]:
                lines.append(f"• {market.get('title') or market.get('question') or 'Untitled'}")
            return "\n".join(lines)
        if action == "autopilot":
            return "🦞 AutoPilot\n\nAucune stratégie active pour le moment."
        if action == "help":
            return "🩺 Help\n\n/smartcopy <nom> <wallet_cible> <portfolio_usdc> [mon_wallet]\nMes paires"
        if action == "smart_copy_prompt":
            return "Smart Copy simulé IA\n\n/smartcopy <nom> <wallet_cible> <portfolio_usdc> [mon_wallet]\nTrade Size: 100% of leader's amount"
        if action == "wallet_create_prompt":
            return (
                "🆕 Nouveau wallet Polymarket\n\n"
                "Wallet signer ETH/POL\n"
                "Wallet proxy Polymarket\n"
                "Copy-trade redémarré après activation"
            )
        if action == "wallet_create_confirm":
            result = super().handle_action(action)
            return result[0] if isinstance(result, tuple) else result
        if action == "top1":
            from services.polymarket_analytics import format_top_wallets_report, get_top_1_percent

            return format_top_wallets_report(get_top_1_percent(min_pnl=0))
        if action == "groq_analyze":
            try:
                scores = WalletRanker().rank()
                return GroqAdvisor().analyze_wallets(scores)
            except Exception as exc:
                return f"Analyse Groq indisponible: {exc}"
        if action == "risk_menu":
            lines = ["Gestion des Risques par Wallet", ""]
            for wallet in Config.TARGET_WALLETS or []:
                lines.append(f"• `{wallet}`")
                lines.append("  Standard Wallet Mirror")
                lines.append("  Mon wallet attribué: auto")
            return "\n".join(lines)
        if action.startswith("risk_wallet_"):
            wallet = action.replace("risk_wallet_", "", 1)
            from services.smart_copy import get_profile

            profile = get_profile(wallet)
            if profile:
                return (
                    "Profil Risque Wallet\n\n"
                    f"{profile.get('name')}\n"
                    f"Mon wallet attribué: `{profile.get('assigned_wallet')}`\n"
                    f"Type: `{profile.get('wallet_type')}`\n"
                    f"Max/trade: `${float(profile.get('single_trade_limit', 0)):.2f}`\n"
                    "Simulation: ON ✅ forcée\n"
                    "Trade Size 100% du leader"
                )
            return "Profil Risque Wallet\n\nStandard Wallet Mirror\nPas de copie all-in\nMon wallet attribué: auto"
        if action == "rank_wallets_themes":
            scores = WalletRanker().rank_by_theme(limit=100)
            return WalletRanker.format_theme_menu(scores)
        if action.startswith("rank_theme_"):
            theme = action.replace("rank_theme_", "")
            if theme == "top10_all":
                return WalletRanker.format_top10_all_themes(getattr(self, "_rank_scores", []))
            scores = getattr(self, "_rank_scores", [])
            return WalletRanker.format_selected_theme_scores(scores, theme)
        result = super().handle_action(action)
        if isinstance(result, tuple):
            return result[0]
        return result

    def keyboard_for_action(self, action: str):
        if action == "scan_wallet":
            return {"inline_keyboard": [[{"text": "🔍 Scanner", "callback_data": "scan_wallet_prompt"}], [{"text": "🏠 Accueil", "callback_data": "menu"}]]}
        if action == "wallet_search":
            return {"inline_keyboard": [[{"text": "🧬 Wallet Search", "callback_data": "wallet_search"}], [{"text": "🏠 Accueil", "callback_data": "menu"}]]}
        if action == "rank_wallets_themes":
            return {
                "inline_keyboard": [
                    [{"text": "🌚 Crypto", "callback_data": "rank_theme_crypto"}, {"text": "🥇 Sport", "callback_data": "rank_theme_sport"}],
                    [{"text": "🏆 Top 50 all thèmes", "callback_data": "rank_theme_top10_all"}],
                    [{"text": "🔄 Thèmes", "callback_data": "rank_wallets_themes"}],
                    [{"text": "🏠 Accueil", "callback_data": "menu"}],
                ]
            }
        if action == "risk_menu":
            return {
                "inline_keyboard": [
                    [{"text": f"⚙️ {wallet[:8]}...{wallet[-6:]}", "callback_data": f"risk_wallet_{wallet}"}]
                    for wallet in (Config.TARGET_WALLETS or [])
                ] + [[{"text": "🏠 Accueil", "callback_data": "menu"}]]
            }
        if action == "wallet_create_prompt":
            return {
                "inline_keyboard": [
                    [{"text": "✅ Créer + activer", "callback_data": "wallet_create_confirm"}],
                    [{"text": "⬅️ Annuler", "callback_data": "my_wallet_full"}],
                ]
            }
        if action.startswith("rank_theme_"):
            theme = action.replace("rank_theme_", "")
            rows = []
            for score in getattr(self, "_rank_scores", []):
                if score.theme == theme:
                    short = f"{score.wallet[:8]}...{score.wallet[-6:]}"
                    rows.append([{"text": f"🔍 #{score.rank} {short}", "callback_data": f"scan_{score.wallet}"}])
            rows.append([{"text": "⬅️ Thèmes", "callback_data": "rank_wallets_themes"}])
            return {"inline_keyboard": rows}
        return super().keyboard_for_action(action)

    def send_message(self, text: str, **kwargs):
        results = []
        payload = {"chat_id": None, "text": self.truncate(text), "parse_mode": "Markdown"}
        payload.update(kwargs)
        for chat_id in getattr(self, "chat_ids", []):
            payload["chat_id"] = chat_id
            try:
                results.append(self.api("sendMessage", dict(payload)))
            except requests.HTTPError as error:
                if getattr(error.response, "status_code", None) == 400 and "parse_mode" in payload:
                    retry_payload = dict(payload)
                    retry_payload.pop("parse_mode", None)
                    results.append(self.api("sendMessage", retry_payload))
                else:
                    raise
        return results

    @staticmethod
    def truncate(text: str, limit: int = 4096) -> str:
        if len(text) <= limit:
            return text
        suffix = "\n\n[output truncated]"
        return text[: max(0, limit - len(suffix))] + suffix

__all__ = [
    "Config",
    "GroqAdvisor",
    "TelegramControlBot",
    "WalletRanker",
    "requests",
]
