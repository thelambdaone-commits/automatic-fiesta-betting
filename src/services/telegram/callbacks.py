"""
Gestion centralisée des callbacks Telegram.
Format: "menu:action" ou "action:param"
"""
from typing import Dict, Callable, Optional
from functools import partial
import re


class CallbackHandler:
    """
    Centralise tous les handlers de callbacks.
    Format moderne: "menu:action" ou "object:action:param"
    """
    
    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
        self._register_defaults()
    
    def _register_defaults(self):
        """Enregistre les handlers par défaut."""
        # Menus principaux (format: "menu:name")
        self.register("menu:main", self._menu_main)
        self.register("menu:copy", self._menu_copy)
        self.register("menu:wallets", self._menu_wallets)
        self.register("menu:discover", self._menu_discover)
        self.register("menu:settings", self._menu_settings)
        self.register("menu:stats", self._menu_stats)
        self.register("menu:strategies", self._menu_strategies)
        self.register("menu:history", self._menu_history)
        
        # Actions (format: "action:name")
        self.register("action:add_strategy", self._action_add_strategy)
        self.register("action:list_strategies", self._action_list_strategies)
        self.register("action:stats", self._action_stats)
        self.register("action:settings", self._action_settings)
        
        # Smart Copy (format: "smartcopy:action:name")
        self.register("smartcopy:create", self._smartcopy_create)
        self.register("smartcopy:list", self._smartcopy_list)
        self.register("smartcopy:edit:", self._smartcopy_edit)  # prefix
        self.register("smartcopy:delete:", self._smartcopy_delete)  # prefix
        self.register("smartcopy:toggle:", self._smartcopy_toggle)  # prefix
        
        # Mirror (format: "mirror:action:param")
        self.register("mirror:add", self._mirror_add)
        self.register("mirror:list", self._mirror_list)
        self.register("mirror:edit:", self._mirror_edit)  # prefix
        self.register("mirror:delete:", self._mirror_delete)  # prefix
        
        # Bot controls (format: "bot:action")
        self.register("bot:pause", self._bot_pause)
        self.register("bot:resume", self._bot_resume)
        self.register("bot:refresh", self._bot_refresh)
    
    def register(self, action: str, handler: Callable):
        """Enregistre un handler pour une action."""
        self.handlers[action] = handler
    
    def handle(self, bot, action: str, *args, **kwargs):
        """Appelle le handler approprié."""
        # Handle new hierarchical menus (format: "menu:xxx")
        if action == "menu":
            return bot.keyboard(), home_text()
        if action == "menu:copy_trading":
            return bot.copy_trading_keyboard(), bot.handle_action("menu:copy_trading")
        if action == "menu:mes_wallets":
            return bot.mes_wallets_keyboard(), bot.handle_action("menu:mes_wallets")
        if action == "menu:decouvrir":
            return bot.decouvrir_keyboard(), bot.handle_action("menu:decouvrir")
        if action == "menu:parametres":
            return bot.parametres_keyboard(), bot.handle_action("menu:parametres")
        
        # Try direct match
        handler = self.handlers.get(action)
        
        # Try prefix match (for "smartcopy:edit:name" etc.)
        if not handler:
            for key, h in self.handlers.items():
                if key.endswith(':') and action.startswith(key):
                    # Extract param
                    param = action[len(key):]
                    return h(bot, param, *args, **kwargs)
        
        if handler:
            return handler(bot, *args, **kwargs)
        
        return f"⚠️ Action inconnue: {action}"
    
        # Menu handlers
        from .ui.menus import start_menu, start_keyboard
        capital = 0.0
        pnl = 0.0
        strategies_count = 0
        try:
            from services.copy_trade import PolymarketTrader
            trader = PolymarketTrader(mode='test')
            balance_info = trader.check_cash_balance()
            if balance_info:
                capital = float(balance_info.get('balance', 0))
        
            from services.smart_copy import load_profiles
            profiles = load_profiles()
            strategies_count = len(profiles) if profiles else 0
        except:
            pass
        
        return start_menu(capital=capital, pnl=pnl, strategies_count=strategies_count), start_keyboard()
    
    def _menu_copy(self, bot):
        from .ui.menus import copy_trading_menu, copy_trading_keyboard
        return copy_trading_menu(), copy_trading_keyboard()
    
    def _menu_wallets(self, bot):
        from .ui.menus import wallets_menu, wallets_keyboard
        wallets = []
        try:
            # Get wallets with balance
            wallets = Config.TARGET_WALLETS or []
        except:
            pass
        return wallets_menu(wallets=wallets), wallets_keyboard()
    
    def _menu_discover(self, bot):
        from .ui.menus import discover_menu, discover_keyboard
        return discover_menu(), discover_keyboard()
    
    def _menu_settings(self, bot):
        from .ui.menus import settings_menu, settings_keyboard
        wallet = ""
        try:
            from eth_account import Account
            wallet = Account.from_key(Config.PRIVATE_KEY).address if Config.PRIVATE_KEY else ""
        except:
            pass
        slippage = getattr(Config, 'SLIPPAGE_TOLERANCE', 0.01) * 100
        mode = "🟢 Simulation" if Config.SIMULATION_MODE or not Config.LIVE_TRADING else "🔴 Réel"
        return settings_menu(wallet=wallet, slippage=slippage, mode=mode), settings_keyboard()
    
    def _menu_stats(self, bot):
        from .ui.menus import stats_premium, stats_keyboard
        return stats_premium(), stats_keyboard()
    
    def _menu_strategies(self, bot):
        from .ui.menus import strategies_list, strategies_keyboard
        strategies = []
        try:
            from services.smart_copy import load_profiles
            profiles = load_profiles()
            for name, profile in profiles.items():
                strategies.append({
                    "name": name,
                    "type": "smartcopy",
                    "capital": float(profile.get('portfolio_amount', 0) or 0),
                    "status": "simulation" if profile.get('simulation', True) else "active",
                })
        except:
            pass
        return strategies_list(strategies), strategies_keyboard(strategies)
    
    def _menu_history(self, bot):
        """Show wallet history with PnL stats."""
        if hasattr(bot, '_wallet_history_text') and hasattr(bot, '_history_page'):
            bot._history_page = 0
            text = bot._wallet_history_text(page=0)
            from services.telegram.keyboards import history_keyboard
            keyboard = history_keyboard(page=0, total_pages=getattr(bot, '_history_total_pages', 1))
            return text, keyboard
        return "📜 *Historique*\n\nFonctionnalité en cours de chargement...", {
            "inline_keyboard": [[{"text": "🏠 Accueil", "callback_data": "menu"}]]
        }
    
    # Action handlers
    def _action_add_strategy(self, bot):
        return "➕ *Ajouter une stratégie*\n\nChoisissez le type :", {
            "inline_keyboard": [
                [{"text": "🧠 Smart Copy IA", "callback_data": "smartcopy:create"}],
                [{"text": "🔁 Wallet Mirror", "callback_data": "mirror:add"}],
                [{"text": "⬅️ Retour", "callback_data": "menu:main"}],
            ]
        }
    
    def _action_list_strategies(self, bot):
        return self._menu_strategies(bot)
    
    def _action_stats(self, bot):
        return self._menu_stats(bot)
    
    def _action_settings(self, bot):
        return self._menu_settings(bot)
    
    # Smart Copy handlers
    def _smartcopy_create(self, bot):
        return "🧠 *Créer Smart Copy*\n\nÉtape 1/5 : Nom de la stratégie ?"
    
    def _smartcopy_list(self, bot):
        return self._menu_strategies(bot)
    
    def _smartcopy_edit(self, bot, strategy_name: str):
        return f"⚙️ *Gérer {strategy_name}*\n\nActions disponibles :", {
            "inline_keyboard": [
                [{"text": "▶️ Activer / ⏸️ Pause", "callback_data": f"smartcopy:toggle:{strategy_name}"}],
                [{"text": "💰 Modifier capital", "callback_data": f"smartcopy:edit_capital:{strategy_name}"}],
                [{"text": "⚡ Modifier max trade", "callback_data": f"smartcopy:edit_max:{strategy_name}"}],
                [{"text": "📉 Modifier slippage", "callback_data": f"smartcopy:edit_slippage:{strategy_name}"}],
                [{"text": "🗑️ Supprimer", "callback_data": f"smartcopy:delete:{strategy_name}"}],
                [{"text": "⬅️ Retour", "callback_data": "menu:strategies"}],
            ]
        }
    
    def _smartcopy_delete(self, bot, strategy_name: str):
        return f"🗑️ *Supprimer {strategy_name}*\n\nÊtes-vous sûr ?", {
            "inline_keyboard": [
                [{"text": "✅ Confirmer", "callback_data": f"smartcopy:delete_confirm:{strategy_name}"}],
                [{"text": "❌ Annuler", "callback_data": f"smartcopy:list"}],
            ]
        }
    
    def _smartcopy_toggle(self, bot, strategy_name: str):
        return f"✅ *{strategy_name}* mis à jour.", {
            "inline_keyboard": [
                [{"text": "⬅️ Retour", "callback_data": "menu:strategies"}],
            ]
        }
    
    # Mirror handlers
    def _mirror_add(self, bot):
        return "🔁 *Ajouter Wallet Mirror*\n\nAdresse du wallet cible ?"
    
    def _mirror_list(self, bot):
        wallets = Config.TARGET_WALLETS or []
        lines = ["🔁 *WALLET MIRRORS*\n"]
        for w in wallets:
            short = f"{w[:8]}...{w[-6:]}" if len(w) > 14 else w
            lines.append(f"• `{short}`")
        lines.append("\n[ ➕ Ajouter ][ ⬅️ Retour ]")
        return "\n".join(lines)
    
    def _mirror_edit(self, bot, wallet: str):
        return f"⚙️ *Gérer Mirror {wallet[:8]}...*\n\nActions :", {
            "inline_keyboard": [
                [{"text": "⏸️ Pause / ▶️ Reprendre", "callback_data": f"mirror:toggle:{wallet}"}],
                [{"text": "💰 Modifier max trade", "callback_data": f"mirror:edit_max:{wallet}"}],
                [{"text": "🗑️ Supprimer", "callback_data": f"mirror:delete:{wallet}"}],
                [{"text": "⬅️ Retour", "callback_data": "menu:strategies"}],
            ]
        }
    
    def _mirror_delete(self, bot, wallet: str):
        return f"🗑️ *Supprimer Mirror ?*\n\n{wallet[:8]}...{wallet[-6:]}", {
            "inline_keyboard": [
                [{"text": "✅ Confirmer", "callback_data": f"mirror:delete_confirm:{wallet}"}],
                [{"text": "❌ Annuler", "callback_data": f"mirror:list"}],
            ]
        }
    
    # Bot control handlers
    def _bot_pause(self, bot):
        if hasattr(bot, '_toggle_pause_resume'):
            return bot._toggle_pause_resume(), bot.keyboard_for_action("status_pause")
        return "⏸️ Bot en pause.", None
    
    def _bot_resume(self, bot):
        if hasattr(bot, '_toggle_pause_resume'):
            return bot._toggle_pause_resume(), bot.keyboard_for_action("status_resume")
        return "▶️ Bot repris.", None
    
    def _bot_refresh(self, bot):
        return self._menu_main(bot)
