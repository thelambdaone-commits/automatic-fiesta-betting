from core.config import Config
from services.telegram.base import logger


class TelegramSettingsMixin:
    """Settings related methods for Telegram bot."""

    def _settings_menu(self) -> str:
        """Display settings menu."""
        mode = "RÉEL" if (not Config.SIMULATION_MODE and Config.LIVE_TRADING) else "Simulation"
        max_trade = float(getattr(Config, "MAX_ORDER_SIZE", 1000))
        slippage = float(getattr(Config, "SLIPPAGE_TOLERANCE", 0.01)) * 100
        
        return (
            "⚙️ *Paramètres du Bot*\n\n"
            f"Mode actuel: *{mode}*\n"
            f"Max/pari: `${max_trade:.2f}`\n"
            f"Slippage: `{slippage:.1f}%`\n\n"
            "Utilise les boutons ci-dessous pour modifier les réglages."
        )

    def _settings_mode(self) -> str:
        """Toggle simulation/live mode."""
        current = "Simulation" if (Config.SIMULATION_MODE or not Config.LIVE_TRADING) else "RÉEL"
        return (
            "🧪 *Mode d'exécution*\n\n"
            f"Mode actuel: *{current}*\n\n"
            "⚠️ Pour passer en mode RÉEL, tu dois:\n"
            "1. Avoir `LIVE_TRADING=true` dans `.env`\n"
            "2. Avoir `CONFIRM_LIVE_TRADING=true`\n"
            "3. Relancer le bot avec `pm2 restart polymarket-telegram`\n\n"
            "Le mode Simulation est recommandé pour tester."
        )

    def _settings_mode_live(self) -> str:
        """Attempt to switch to live mode."""
        if Config.LIVE_TRADING and getattr(Config, "CONFIRM_LIVE_TRADING", False):
            Config.SIMULATION_MODE = False
            return (
                "✅ *Mode RÉEL activé*\n\n"
                "Le bot va maintenant exécuter des paris réels.\n"
                "⚠️ Surveille les logs avec `pm2 logs polymarket-copytrade`"
            )
        return (
            "❌ *Impossible d'activer le mode RÉEL*\n\n"
            "Vérifie tes réglages dans `.env`:\n"
            "• `LIVE_TRADING=true`\n"
            "• `CONFIRM_LIVE_TRADING=true`\n\n"
            "Puis redémarre le bot."
        )

    def _settings_max_trade(self) -> str:
        """Configure max trade size."""
        return (
            "💰 *Limite par pari*\n\n"
            "Cette limite s'applique à tous les paris (Wallet Mirror et Smart Copy).\n\n"
            "Pour modifier, édite `MAX_ORDER_SIZE` dans `.env`:\n"
            "```\nMAX_ORDER_SIZE=1000\n```\n\n"
            "Puis redémarre le bot avec `pm2 restart all`."
        )

    def _settings_slippage(self) -> str:
        """Configure slippage tolerance."""
        return (
            "🎯 *Slippage tolerance*\n\n"
            "Le slippage définit la fourchette de prix acceptable pour l'exécution.\n\n"
            "Pour modifier, édite `SLIPPAGE_TOLERANCE` dans `.env`:\n"
            "```\nSLIPPAGE_TOLERANCE=0.01\n```\n"
            "(0.01 = 1% de slippage maximum)\n\n"
            "Puis redémarre le bot avec `pm2 restart all`."
        )

    def _risk_settings_text(self) -> str:
        """Risk settings text."""
        return (
            "🛡️ *Réglages des risques*\n\n"
            "• Stop-Loss: automatique à -10% (simulation)\n"
            "• Take-Profit: automatique à +20% (simulation)\n"
            "• Max position: 20% du portfolio par pari\n"
            "• Pause auto: si perte > 5% sur 1h\n\n"
            "Ces réglages s'appliquent au mode Simulation.\n"
            "Mode RÉEL: les ordres sont envoyés tels quels."
        )

    def _slippage_settings_text(self) -> str:
        """Slippage settings text."""
        slippage = float(getattr(Config, "SLIPPAGE_TOLERANCE", 0.01)) * 100
        return (
            "🎯 *Slippage tolerance*\n\n"
            f"Valeur actuelle: `{slippage:.1f}%`\n\n"
            "Le slippage permet d'accepter une variation de prix.\n"
            "Valeurs recommandées:\n"
            "• 0.5% pour les marchés liquides\n"
            "• 1% pour les marchés normaux\n"
            "• 2% pour les marchés volatils\n\n"
            "Modifier dans `.env`: `SLIPPAGE_TOLERANCE=0.01`"
        )

    def _risk_alerts_text(self) -> str:
        """Risk alerts text."""
        return (
            "🔔 *Alertes de risque*\n\n"
            "Le bot envoie des alertes quand:\n"
            "• Une transaction échoue\n"
            "• Le solde USDC est bas (< $50)\n"
            "• Une erreur de réseau survient\n"
            "• Le WebSocket se déconnecte\n\n"
            "Pour désactiver, modifie `TELEGRAM_ALERTS=false` dans `.env`."
        )
