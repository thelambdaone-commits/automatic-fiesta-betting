import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class CopyBettingKeyboardMixin:
    """Copy betting related keyboards."""
    
    @staticmethod
    def copy_trading_keyboard() -> Dict:
        """Copy Trading submenu."""
        return {
            "inline_keyboard": [
                [
                    {"text": "📊 Mes stratégies", "callback_data": "menu:copy_strategies"},
                    {"text": "➕ Ajouter stratégie", "callback_data": "menu:copy_add"},
                ],
                [
                    {"text": "🦞 Smart Copy IA", "callback_data": "smartcopy_ai_menu"},
                    {"text": "🛰️ AutoPilot", "callback_data": "autopilot"},
                ],
                [
                    {"text": "📈 Performance", "callback_data": "performance"},
                    {"text": "⬅️ Retour", "callback_data": "menu"},
                ],
                [
                    {"text": "❌ Fermer", "callback_data": "close_menu"},
                ],
            ]
        }
    
    @staticmethod
    def mirror_keyboard() -> Dict:
        """Mirror wallet keyboard."""
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
        """Smart Copy AI menu keyboard."""
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
        """Smart Copy mode selection keyboard."""
        return {
            "inline_keyboard": [
                [
                    {"text": "🧪 Simulation", "callback_data": "smartcopy_mode_sim"},
                    {"text": "🔴 Mode : RÉEL", "callback_data": "smartcopy_mode_live"},
                ],
                [
                    {"text": "⬅️ Retour", "callback_data": "smartcopy_ai_menu"},
                ],
            ]
        }
    
    @staticmethod
    def smartcopy_input_keyboard() -> Dict:
        """Smart Copy input keyboard."""
        return {
            "inline_keyboard": [
                [
                    {"text": "🧪 Simulation", "callback_data": "smartcopy_mode_sim"},
                    {"text": "🔴 Mode : RÉEL", "callback_data": "smartcopy_mode_live"},
                ],
                [
                    {"text": "⬅️ Retour", "callback_data": "smartcopy_ai_menu"},
                ],
            ]
        }
    
    @staticmethod
    def smartcopy_confirm_keyboard() -> Dict:
        """Smart Copy confirm keyboard."""
        return {
            "inline_keyboard": [
                [
                    {"text": "✅ Confirmer", "callback_data": "smartcopy_execute"},
                    {"text": "❌ Annuler", "callback_data": "smartcopy_cancel"},
                ],
                [
                    {"text": "⬅️ Retour", "callback_data": "smartcopy_ai_menu"},
                ],
            ]
        }
    
    @staticmethod
    def trades_keyboard() -> Dict:
        """Trades list keyboard."""
        return {
            "inline_keyboard": [
                [
                    {"text": "🔄 Actualiser", "callback_data": "active_trades"},
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        }
    
    @staticmethod
    def history_keyboard(page: int = 0, total_trades: int = 0, page_size: int = 5) -> Dict:
        """History keyboard with pagination."""
        total_pages = (total_trades + page_size - 1) // page_size if total_trades > 0 else 1
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
        
        # Action rows
        rows.append([
            {"text": "📜 Historique", "callback_data": "trade_history"},
            {"text": "📋 Ordres", "callback_data": "wallet_orders"},
            {"text": "💼 Positions", "callback_data": "wallet_positions"},
        ])
        rows.append([
            {"text": "🔄 Actualiser", "callback_data": "history_refresh"},
            {"text": "🏠 Accueil", "callback_data": "menu"},
        ])
        rows.append([
            {"text": "⬅️ Retour", "callback_data": "menu:mes_wallets"},
        ])
        
        return {"inline_keyboard": rows}
