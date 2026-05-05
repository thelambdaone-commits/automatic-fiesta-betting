import logging
from typing import Dict

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handles incoming messages and text processing."""
    
    def handle_text(self, text: str, chat_id: str):
        """Handle non-command text messages."""
        # Try to process as smart copy configuration
        if text.startswith("/smartcopy"):
            result = self._handle_smartcopy_message(text)
            self.send_message(result, chat_id=chat_id)
        elif text.startswith("/mirror"):
            result = self._handle_mirror_message(text)
            self.send_message(result, chat_id=chat_id)
        else:
            self.send_message(
                "Commande inconnue. Utilise /start pour voir le menu principal.",
                chat_id=chat_id
            )
    
    def handle_scan_message(self, text: str) -> str:
        """Handle /scan command."""
        parts = text.split()
        if len(parts) < 2:
            return "Usage: /scan <wallet_ou_@profil>"

        target = parts[1].strip()
        try:
            from services.polymarket_profile import resolve_polymarket_profile

            wallet = resolve_polymarket_profile(target)
            prefix = f"Profil `{target}` résolu en `{wallet}`.\n\n" if target != wallet else ""
            return prefix + self._scan_wallet_result(wallet)
        except Exception as e:
            logger.error("Scan message handling failed: %s", e)
            return f"❌ Erreur lors de l'analyse: {e}"
    
    def _handle_smartcopy_message(self, text: str) -> str:
        """Handle /smartcopy command."""
        try:
            from services.telegram.copy_modules.smart import TelegramCopySmartMixin
            handler = TelegramCopySmartMixin()
            return handler.handle_smartcopy_message(text)
        except Exception as e:
            logger.error(f"Smart copy message handling failed: {e}")
            return "❌ Erreur lors du traitement de la commande Smart Copy."
    
    def _handle_mirror_message(self, text: str) -> str:
        """Handle /mirror command."""
        parts = text.split()
        if len(parts) < 2:
            return "Usage: /mirror <wallet_ou_@profil>"
        
        target = parts[1].strip()
        try:
            from services.polymarket_profile import resolve_polymarket_profile
            from services.telegram.copy_modules.mirror import TelegramCopyMirrorMixin

            wallet = resolve_polymarket_profile(target)
            handler = TelegramCopyMirrorMixin()
            handler._save_wallet_mirror_target(wallet)
            prefix = f"`{target}` → " if target != wallet else ""
            return f"✅ Wallet {prefix}`{wallet}` ajouté aux cibles."
        except Exception as e:
            logger.error(f"Mirror message handling failed: {e}")
            return f"❌ Erreur lors de l'ajout du wallet: {e}"
