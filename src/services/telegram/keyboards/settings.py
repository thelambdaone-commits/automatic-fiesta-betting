import logging
from typing import Dict, List, Optional

from core.config import Config

logger = logging.getLogger(__name__)


class SettingsKeyboardMixin:
    """Settings related keyboards."""
    
    @staticmethod
    def parametres_keyboard() -> Dict:
        """Paramètres submenu."""
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
    def settings_keyboard() -> Dict:
        """Settings main keyboard."""
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
    
    def risk_keyboard(self) -> Dict:
        """Risk settings keyboard."""
        rows = []
        if hasattr(self, '_risk_wallet_rows'):
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
    def errors_keyboard() -> Dict:
        """Errors page keyboard."""
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
        """Performance page keyboard."""
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
        """Smart Copy dashboard with toggle buttons."""
        if profiles is None:
            try:
                from services.smart_copy import load_profiles
                profiles = load_profiles()
            except Exception as e:
                logger.debug("Unable to load Smart Copy profiles: %s", e)
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
