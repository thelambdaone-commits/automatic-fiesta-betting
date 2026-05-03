import logging
from typing import Dict, List

from core.config import Config
from services.telegram.ui.home import home_text

logger = logging.getLogger(__name__)


class MainKeyboardMixin:
    """Main menu keyboards."""
    
    @staticmethod
    def keyboard() -> Dict:
        """Main menu - 4 buttons max."""
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
                [
                    {"text": "❌ Fermer", "callback_data": "close_menu"},
                ],
            ]
        }
    
    @staticmethod
    def menu_next_keyboard() -> Dict:
        """Secondary menu page."""
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
