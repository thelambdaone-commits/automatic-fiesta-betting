import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"
SCRIPTS_DIR = ROOT_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

from check_setup import format_results, run_checks
from core.config import Config
from services.groq_advisor import GroqAdvisor
from services.wallet_ranker import THEME_ALL_DISPLAY_LIMIT, THEME_DETAIL_DISPLAY_LIMIT, THEME_RANK_LIMIT, WalletRanker

logger = logging.getLogger(__name__)


class TelegramKeyboardMixin:
    @staticmethod
    def keyboard() -> Dict:
        """Menu principal - 4 boutons max."""
        return {
            "inline_keyboard": [
                [
                    {"text": "🔗 Copy Betting", "callback_data": "menu:copy_trading"},
                ],
                [
                    {"text": "👛 Mes wallets", "callback_data": "menu:mes_wallets"},
                ],
                [
                    {"text": "🧭 Découvrir", "callback_data": "menu:decouvrir"},
                ],
                [
                    {"text": "⚙️ Paramètres", "callback_data": "menu:parametres"},
                ],
            ]
        }

    @staticmethod
    def copy_trading_keyboard() -> Dict:
        """Sous-menu Copy Trading."""
        return {
            "inline_keyboard": [
                [
                    {"text": "📊 Mes stratégies", "callback_data": "menu:copy_strategies"},
                    {"text": "➕ Ajouter stratégie", "callback_data": "menu:copy_add"},
                ],
                [
                    {"text": "🦞 Smart Copy IA", "callback_data": "smartcopy_ai_menu"},
                    {"text": "📡 AutoPilot", "callback_data": "autopilot"},
                ],
                [
                    {"text": "📊 Statut", "callback_data": "status"},
                    {"text": "⬅️ Retour", "callback_data": "menu"},
                ],
            ]
        }

    @staticmethod
    def mes_wallets_keyboard() -> Dict:
        """Sous-menu Mes wallets."""
        return {
            "inline_keyboard": [
                [
                    {"text": "👀 Mes wallets", "callback_data": "wallet_mirror"},
                    {"text": "➕ Ajouter", "callback_data": "mirror_add_prompt"},
                ],
                [
                    {"text": "🔍 Rechercher un wallet", "callback_data": "wallet_search"},
                    {"text": "🎲 Pari manuel", "callback_data": "manual_trade"},
                ],
                [
                    {"text": "📜 Historique", "callback_data": "trade_history"},
                    {"text": "⬅️ Retour", "callback_data": "menu"},
                ],
            ]
        }

    @staticmethod
    def decouvrir_keyboard() -> Dict:
        """Sous-menu Découvrir."""
        return {
            "inline_keyboard": [
                [
                    {"text": "🔍 Scanner Wallet", "callback_data": "scan_wallet_prompt"},
                    {"text": "🎯 Top wallets", "callback_data": "top_wallets_menu"},
                ],
                [
                    {"text": "🐋 Whales", "callback_data": "whale_activity"},
                    {"text": "🔎 Marchés", "callback_data": "market_search"},
                ],
                [
                    {"text": "🧠 IA", "callback_data": "ia_analysis"},
                    {"text": "📊 Par thème", "callback_data": "trades_theme"},
                ],
                [
                    {"text": "❓ Help", "callback_data": "help"},
                    {"text": "⬅️ Retour", "callback_data": "menu"},
                ],
            ]
        }

    @staticmethod
    def parametres_keyboard() -> Dict:
        """Sous-menu Paramètres."""
        return {
            "inline_keyboard": [
                [
                    {"text": "🧪 Mode : Simulation", "callback_data": "settings_menu"},
                    {"text": "🎯 Slippage", "callback_data": "settings_slippage"},
                ],
                [
                    {"text": "👛 Wallet principal", "callback_data": "my_wallet"},
                    {"text": "🔔 Notifications", "callback_data": "settings_notif"},
                ],
                [
                    {"text": "🗑️ Supprimer compte", "callback_data": "settings_delete"},
                    {"text": "⬅️ Retour", "callback_data": "menu"},
                ],
            ]
        }

    @staticmethod
    def menu_next_keyboard() -> Dict:
        return {
            "inline_keyboard": [
                [
                    {"text": "📊 Paris par thème", "callback_data": "trades_theme"},
                    {"text": "🧭 Découvrir", "callback_data": "discover"},
                ],
                [
                    {"text": "🦞 Smart Copy IA", "callback_data": "smartcopy_ai_menu"},
                    {"text": "🛡️ Risques", "callback_data": "risk_menu"},
                ],
                [
                    {"text": "📡 AutoPilot", "callback_data": "autopilot"},
                    {"text": "📊 Statut", "callback_data": "status"},
                ],
                [
                    {"text": "⬅️ Accueil", "callback_data": "menu"},
                ],
            ]
        }

    @staticmethod
    def paris_theme_keyboard() -> Dict:
        return {
            "inline_keyboard": [
                [{"text": "🗳️ Politique", "callback_data": "theme_politique"}],
                [{"text": "⚽ Sport", "callback_data": "theme_sport"}],
                [{"text": "💰 Crypto", "callback_data": "theme_crypto"}],
                [{"text": "🌍 Monde", "callback_data": "theme_world"}],
                [{"text": "⬅️ Retour", "callback_data": "menu"}],
            ]
        }

    @staticmethod
    def mirror_keyboard() -> Dict:
        return {
            "inline_keyboard": [
                [
                    {"text": "➕ Ajouter wallet", "callback_data": "mirror_add_prompt"},
                    {"text": "🔗 Mes paires", "callback_data": "copy_pairs"},
                ],
                [
                    {"text": "📊 Profils", "callback_data": "smart_copy_dashboard"},
                    {"text": "🧪 Simulation", "callback_data": "simulate_trade"},
                ],
                [
                    {"text": "🗑️ Supprimer", "callback_data": "mirror_remove_menu"},
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        }

    @staticmethod
    def smartcopy_ai_menu_keyboard() -> Dict:
        return {
            "inline_keyboard": [
                [
                    {"text": "➕ Créer un copytrade", "callback_data": "smartcopy_create"},
                ],
                [
                    {"text": "📊 Profils IA", "callback_data": "smart_copy_dashboard"},
                    {"text": "🧪 Simulation", "callback_data": "simulate_trade"},
                ],
                [
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        }

    @staticmethod
    def smartcopy_mode_keyboard() -> Dict:
        return {
            "inline_keyboard": [
                [
                    {"text": "🧪 Simulation", "callback_data": "smartcopy_mode_sim"},
                    {"text": "🔴 Mode : RÉEL", "callback_data": "smartcopy_mode_live"},
                ],
                [
                    {"text": "⬅️ Retour", "callback_data": "smartcopy_ai_menu"},
                    {"text": "❌ Annuler", "callback_data": "smartcopy_cancel"},
                ],
            ]
        }

    @staticmethod
    def smartcopy_input_keyboard() -> Dict:
        return {
            "inline_keyboard": [
                [
                    {"text": "⬅️ Retour", "callback_data": "smartcopy_create"},
                    {"text": "❌ Annuler", "callback_data": "smartcopy_cancel"},
                ],
            ]
        }

    @staticmethod
    def smartcopy_confirm_keyboard() -> Dict:
        return {
            "inline_keyboard": [
                [
                    {"text": "✅ Confirmer", "callback_data": "smartcopy_execute"},
                    {"text": "❌ Annuler", "callback_data": "smartcopy_cancel"},
                ],
                [
                    {"text": "💼 Choisir mon wallet", "callback_data": "smartcopy_choose_wallet"},
                ],
            ]
        }

    @staticmethod
    def manual_trade_keyboard() -> Dict:
        return {
            "inline_keyboard": [
                [
                    {"text": "🟢 Acheter", "callback_data": "manual_buy_prompt"},
                    {"text": "🔴 Vendre", "callback_data": "manual_sell_prompt"},
                ],
                [
                    {"text": "💰 Solde", "callback_data": "check_balance"},
                    {"text": "🔍 Chercher marché", "callback_data": "market_search"},
                ],
                [
                    {"text": "🧪 Simulation", "callback_data": "simulate_trade"},
                    {"text": "🛡️ Risques", "callback_data": "risk_menu"},
                ],
                [
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        }

    def mirror_remove_keyboard(self) -> Dict:
        wallets = Config.TARGET_WALLETS or []
        rows = []
        for wallet in wallets:
            short = f"{wallet[:8]}...{wallet[-6:]}" if len(wallet) > 14 else wallet
            rows.append([{"text": f"🗑️ {short}", "callback_data": f"mirror_remove_{wallet}"}])
        rows.append([{"text": "⬅️ Copier", "callback_data": "wallet_mirror"}])
        rows.append([{"text": "🏠 Accueil", "callback_data": "menu"}])
        return {"inline_keyboard": rows}

    @staticmethod
    def market_search_keyboard() -> Dict:
        return {
            "inline_keyboard": [
                [
                    {"text": "🏛️ Politics", "callback_data": "market_filter_politics"},
                    {"text": "🥇 Sports", "callback_data": "market_filter_sports"},
                ],
                [
                    {"text": "🌚 Crypto", "callback_data": "market_filter_crypto"},
                    {"text": "🦅 Trump", "callback_data": "market_filter_trump"},
                ],
                [
                    {"text": "💹 Finance", "callback_data": "market_filter_finance"},
                    {"text": "🌍 Geopolitics", "callback_data": "market_filter_geopolitics"},
                ],
                [
                    {"text": "📊 Volume", "callback_data": "market_filter_volume"},
                    {"text": "🔥 Trending", "callback_data": "market_filter_trending"},
                ],
                [
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        }

    @staticmethod
    def autopilot_keyboard() -> Dict:
        return {
            "inline_keyboard": [
                [
                    {"text": "📊 Activity", "callback_data": "autopilot_activity"},
                    {"text": "➕ New", "callback_data": "autopilot_new"},
                ],
                [
                    {"text": "🔄 Refresh", "callback_data": "autopilot"},
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        }

    @staticmethod
    def wallet_search_keyboard() -> Dict:
        return {
            "inline_keyboard": [
                [
                    {"text": "🧭 Découvrir", "callback_data": "discover"},
                    {"text": "🎯 Par thèmes", "callback_data": "rank_wallets_themes"},
                ],
                [
                    {"text": "🔍 Scanner Wallet", "callback_data": "scan_wallet_prompt"},
                    {"text": "🧠 Analyse IA", "callback_data": "ia_analysis"},
                ],
                [
                    {"text": "💯 Top wallets", "callback_data": "rank_wallets"},
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        }

    @staticmethod
    def whale_activity_keyboard() -> Dict:
        return {
            "inline_keyboard": [
                [
                    {"text": "⬅️", "callback_data": "whale_prev"},
                    {"text": "➡️", "callback_data": "whale_next"},
                    {"text": "❌", "callback_data": "whale_close"},
                ],
                [
                    {"text": "🔄 Actualiser", "callback_data": "whale_activity"},
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        }

    def keyboard_for_action(self, action: str) -> Dict:
        if action == "menu_next":
            return self.menu_next_keyboard()
        if action == "trades_theme" or action.startswith("theme_"):
            return self.paris_theme_keyboard()
        if action == "market_search" or action.startswith("market_filter_"):
            return self.market_search_keyboard()
        if action.startswith("whale_"):
            return self.whale_activity_keyboard()
        if action == "wallet_search":
            return self.wallet_search_keyboard()
        if action in {"wallet_mirror", "mirror_add_prompt", "copy_pairs", "toggle_copy", "smart_copy_prompt"}:
            return self.mirror_keyboard()
        if action == "smartcopy_ai_menu":
            return self.smartcopy_ai_menu_keyboard()
        if action == "smart_copy_dashboard":
            return self.smartcopy_dashboard_keyboard()
        if action.startswith("quick_copy_"):
            # Quick Copy flow - show mode selection
            return self.smartcopy_mode_keyboard()
        if action == "smartcopy_create":
            return self.smartcopy_mode_keyboard()
        if action == "smartcopy_mode_live" and (Config.SIMULATION_MODE or not Config.LIVE_TRADING):
            return self.smartcopy_mode_keyboard()
        if action in {"smartcopy_mode_sim", "smartcopy_mode_live"}:
            return self.smartcopy_input_keyboard()
        if action == "smartcopy_choose_wallet":
            return self.smartcopy_input_keyboard()
        if action == "smartcopy_confirm":
            return self.smartcopy_confirm_keyboard()
        if action == "smartcopy_execute":
            return self.smartcopy_dashboard_keyboard()
        if action == "smartcopy_cancel":
            return self.smartcopy_ai_menu_keyboard()
        if action.startswith("mirror_remove"):
            return self.mirror_remove_keyboard()
        if action.startswith("manual_") or action in {"manual_trade", "check_balance"}:
            return self.manual_trade_keyboard()
        if action == "scan_wallet":
            return self.keyboard()
        if action == "autopilot" or action.startswith("autopilot_"):
            return self.autopilot_keyboard()
        if action in {"settings_menu", "settings_mode", "settings_mode_live", "settings_max_trade", "settings_slippage"}:
            return self.settings_keyboard()
        if action == "rank_wallets_themes":
            return self.top_wallets_themes_keyboard()
        if action == "rank_theme_top10_all":
            return self.top_wallets_top10_all_keyboard()
        if action.startswith("rank_theme_"):
            return self.top_wallets_theme_detail_keyboard()
        if action.startswith("rank_") or action in {"groq_analyze", "top1", "top_wallets_menu"}:
            return self.top_wallets_page_keyboard()
        if action in {"risk_settings", "slippage_settings", "risk_alerts", "risk_menu"} or action.startswith("risk_wallet_"):
            return self.risk_keyboard()
        if action in {"active_trades", "trade_history"}:
            return self.trades_keyboard()
        return self.keyboard()
    
    @staticmethod
    def _risk_wallet_rows() -> List[List[Dict]]:
        rows = []
        for wallet in Config.TARGET_WALLETS or []:
            short = WalletRanker.short_wallet(wallet)
            rows.append([{"text": f"🛡️ {short}", "callback_data": f"risk_wallet_{wallet}"}])
            if len(rows) >= 8:
                break
        return rows

    def risk_keyboard(self) -> Dict:
        rows = self._risk_wallet_rows()
        rows.extend(
            [
                [
                    {"text": "📊 Profils IA", "callback_data": "smart_copy_dashboard"},
                    {"text": "🧪 Simulation", "callback_data": "simulate_trade"},
                ],
                [
                    {"text": "🪞 Wallet Mirror", "callback_data": "wallet_mirror"},
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        )
        return {"inline_keyboard": rows}
    
    @staticmethod
    def settings_keyboard() -> Dict:
        """Centre de contrôle ⚙️ Paramètres."""
        return {
            "inline_keyboard": [
                [
                    {"text": "🧪 Mode : Simulation", "callback_data": "settings_mode"},
                    {"text": "🔴 Mode : RÉEL", "callback_data": "settings_mode_live"},
                ],
                [
                    {"text": "💰 Max/trade", "callback_data": "settings_max_trade"},
                    {"text": "🎯 Slippage", "callback_data": "settings_slippage"},
                ],
                [
                    {"text": "🛡️ Risques", "callback_data": "risk_menu"},
                ],
                [
                    {"text": "📊 Statut", "callback_data": "status"},
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        }
    
    @staticmethod
    def trades_keyboard() -> Dict:
        return {
            "inline_keyboard": [
                [
                    {"text": "🔄 Actualiser", "callback_data": "active_trades"},
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        }
    
    def history_keyboard(self, page: int = 0, total_pages: int = 1) -> Dict:
        """Keyboard for history with pagination."""
        rows = []
        
        # Navigation row
        nav_row = []
        if page > 0:
            nav_row.append({"text": "⬅️", "callback_data": "history_prev"})
        nav_row.append({"text": f"{page + 1}/{total_pages}", "callback_data": "history"})
        if (page + 1) < total_pages:
            nav_row.append({"text": "➡️", "callback_data": "history_next"})
        if nav_row:
            rows.append(nav_row)
        
        # Action row
        rows.append([
            {"text": "🔄 Refresh", "callback_data": "history_refresh"},
            {"text": "🏠 Accueil", "callback_data": "menu"},
        ])
        
        return {"inline_keyboard": rows}
    
    @staticmethod
    def errors_keyboard() -> Dict:
        """Keyboard for errors page."""
        return {
            "inline_keyboard": [
                [
                    {"text": "🔄 Refresh", "callback_data": "errors"},
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        }
    
    @staticmethod
    def performance_keyboard() -> Dict:
        """Keyboard for performance page."""
        return {
            "inline_keyboard": [
                [
                    {"text": "🔄 Refresh", "callback_data": "performance"},
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        }

    @staticmethod
    def smartcopy_dashboard_keyboard(profiles: Optional[Dict] = None) -> Dict:
        """Keyboard for Smart Copy dashboard with toggle buttons."""
        if profiles is None:
            try:
                from services.smart_copy import load_profiles

                profiles = load_profiles()
            except Exception as e:
                logger.debug("Unable to load Smart Copy profiles for dashboard keyboard: %s", e)
                profiles = {}

        buttons = []
        
        # Add toggle buttons for each profile
        for wallet, profile in profiles.items():
            name = profile.get("name", "Smart Copy")
            enabled = profile.get("enabled", True)
            status = "⏸️ Pause" if enabled else "✅ Activer"
            callback = f"smartcopy_toggle_{wallet}"
            buttons.append([{"text": f"{status}: {name}", "callback_data": callback}])
        
        # Standard navigation buttons
        buttons.append([
            {"text": "🦞 Nouveau Smart Copy", "callback_data": "smartcopy_create"},
        ])
        buttons.append([
            {"text": "🏠 Accueil", "callback_data": "menu"},
            {"text": "⚙️ Paramètres", "callback_data": "settings_menu"},
        ])
        
        return {"inline_keyboard": buttons}
