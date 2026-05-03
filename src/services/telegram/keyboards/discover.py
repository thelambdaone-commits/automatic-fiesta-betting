import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class DiscoverKeyboardMixin:
    """Discover related keyboards."""
    
    @staticmethod
    def decouvrir_keyboard() -> Dict:
        """Découvrir submenu."""
        return {
            "inline_keyboard": [
                [
                    {"text": "🔍 Scanner Wallet", "callback_data": "scan_wallet_prompt"},
                    {"text": "🎯 Top wallets", "callback_data": "top_wallets_menu"},
                ],
                [
                    {"text": "🐋 Whales", "callback_data": "whale_activity"},
                    {"text": "🔥 Top marchés", "callback_data": "top_markets"},
                ],
                [
                    {"text": "🧠 IA", "callback_data": "ia_analysis"},
                    {"text": "📊 Marchés par thème", "callback_data": "market_themes"},
                ],
                [
                    {"text": "❓ Help", "callback_data": "help"},
                    {"text": "⬅️ Retour", "callback_data": "menu"},
                ],
            ]
        }
    
    @staticmethod
    def paris_theme_keyboard() -> Dict:
        """Markets by theme keyboard."""
        return {
            "inline_keyboard": [
                [{"text": "🗳️ Politique", "callback_data": "theme_politique"}],
                [{"text": "⚽ Sport", "callback_data": "theme_sport"}],
                [{"text": "💰 Crypto", "callback_data": "theme_crypto"}],
                [{"text": "🌍 Monde", "callback_data": "theme_world"}],
                [{"text": "🔥 Top marchés", "callback_data": "top_markets"}],
                [{"text": "⬅️ Retour", "callback_data": "menu:decouvrir"}],
            ]
        }

    @staticmethod
    def top_markets_keyboard() -> Dict:
        return {
            "inline_keyboard": [
                [
                    {"text": "🔄 Actualiser", "callback_data": "top_markets"},
                    {"text": "📊 Par thème", "callback_data": "market_themes"},
                ],
                [
                    {"text": "🔎 Rechercher", "callback_data": "market_search"},
                    {"text": "⬅️ Découvrir", "callback_data": "menu:decouvrir"},
                ],
                [
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        }
    
    @staticmethod
    def market_search_keyboard() -> Dict:
        """Market search keyboard."""
        return {
            "inline_keyboard": [
                [
                    {"text": "🔍 Rechercher", "callback_data": "market_search"},
                    {"text": "🧭 Découvrir", "callback_data": "discover"},
                ],
                [
                    {"text": "📊 Statut", "callback_data": "status"},
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        }
    
    @staticmethod
    def wallet_search_keyboard() -> Dict:
        """Wallet search keyboard."""
        return {
            "inline_keyboard": [
                [
                    {"text": "🔍 Scanner Wallet", "callback_data": "scan_wallet_prompt"},
                    {"text": "🧭 Découvrir", "callback_data": "discover"},
                ],
                [
                    {"text": "📊 Statut", "callback_data": "status"},
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        }
    
    @staticmethod
    def autopilot_keyboard() -> Dict:
        """Autopilot keyboard."""
        return {
            "inline_keyboard": [
                [
                    {"text": "▶️ Activer", "callback_data": "autopilot_start"},
                    {"text": "⏸️ Pause", "callback_data": "autopilot_pause"},
                ],
                [
                    {"text": "🧭 Découvrir", "callback_data": "discover"},
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        }
    
    @staticmethod
    def whale_activity_keyboard() -> Dict:
        """Whale activity keyboard."""
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
