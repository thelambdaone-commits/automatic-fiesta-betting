import logging
from typing import Dict, List

from core.config import Config
from services.wallet_ranker import WalletRanker

logger = logging.getLogger(__name__)


def _short_wallet(wallet: str) -> str:
    return f"{wallet[:6]}...{wallet[-3:]}" if wallet and len(wallet) >= 12 else (wallet or "")


class WalletsKeyboardMixin:
    """Wallets related keyboards."""
    
    def mes_wallets_keyboard(self) -> Dict:
        """Mes wallets submenu."""
        active_wallet = self._active_wallet() if hasattr(self, "_active_wallet") else ""
        has_active = bool(active_wallet)
        
        # Dynamic trade button based on active wallet
        if has_active:
            trade_btn = {"text": "🎲 Pari manuel", "callback_data": "manual_trade"}
        else:
            trade_btn = {"text": "🎲 Sélectionner un wallet", "callback_data": "user_wallet_select"}
        
        return {
            "inline_keyboard": [
                [
                    {"text": "🎯 Voir les mirroirs", "callback_data": "wallet_mirror"},
                    {"text": "➕ Ajouter un mirroir", "callback_data": "mirror_add_prompt"},
                ],
                [
                    {"text": "🧬 Mes Wallets", "callback_data": "my_wallet_full"},
                    {"text": "🔍 Chercher un wallet", "callback_data": "wallet_search"},
                ],
                [
                    {"text": "📜 Mon historique", "callback_data": "trade_history"},
                    {"text": "🎲 Pari manuel", "callback_data": "manual_trade"},
                ],
                [
                    {"text": "📲 Changer de mirroir actif", "callback_data": "user_wallet_select"},
                ],
                [
                    {"text": "⬅️ Retour", "callback_data": "menu"},
                    {"text": "❌ Fermer", "callback_data": "close_menu"},
                ],
            ]
        }

    def wallet_selection_keyboard(self) -> Dict:
        """Wallet list with active wallet selector."""
        rows = []
        active = self._active_wallet() if hasattr(self, "_active_wallet") else ""
        wallets = self._configured_wallets() if hasattr(self, "_configured_wallets") else (Config.TARGET_WALLETS or [])
        for wallet in wallets[:10]:
            selected = wallet.lower() == (active or "").lower()
            label = f"{'⭐ ' if selected else ''}{_short_wallet(wallet)}"
            rows.append([{"text": label, "callback_data": f"select_wallet:{wallet}"}])
        rows.extend(
            [
                [
                    {"text": "➕ Ajouter un mirroir", "callback_data": "mirror_add_prompt"},
                    {"text": "⬅️ Mirroirs", "callback_data": "menu:mes_wallets"},
                ],
                [
                    {"text": "❌ Fermer", "callback_data": "close_menu"},
                ],
            ]
        )
        return {"inline_keyboard": rows}
    
    @staticmethod
    def manual_trade_keyboard() -> Dict:
        """Manual trade keyboard."""
        return {
            "inline_keyboard": [
                [
                    {"text": "🧪 Simulation", "callback_data": "simulate_trade"},
                    {"text": "🔴 Mode : RÉEL", "callback_data": "settings_mode_live"},
                ],
                [
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                    {"text": "⬅️ Retour", "callback_data": "menu:mes_wallets"},
                ],
            ]
        }
    
    def mirror_remove_keyboard(self) -> Dict:
        """Remove mirror wallet keyboard."""
        wallets = Config.TARGET_WALLETS or []
        rows = []
        for wallet in wallets[:8]:  # Max 8 buttons
            short = WalletRanker.short_wallet(wallet)
            rows.append([{"text": f"🗑️ {short}", "callback_data": f"mirror_remove_{wallet}"}])
        
        rows.append([
            {"text": "⬅️ Retour", "callback_data": "menu:mes_wallets"},
        ])
    
        return {"inline_keyboard": rows}
