from core.config import Config
from services.telegram.base import logger


class TelegramCopySimulationMixin:
    """Simulation mode related methods."""

    def _simulate_trade_text(self) -> str:
        try:
            from services.smart_copy import load_profiles

            profiles = load_profiles()
        except Exception:
            profiles = {}

        lines = [
            "*🧪 Mode Simulation IA*",
            "",
            f"Mode global: `{'SIMULATION' if Config.SIMULATION_MODE or not Config.LIVE_TRADING else 'RÉEL'}`",
            "Smart Copy: `SIMULATION FORCÉE`",
            "",
            "Règles Smart Copy :",
            "• 100% du montant leader",
            "• Plafond $10 par pari",
            "• Filtre de prix : aucun",
            "• Slippage : tous les prix",
            "• TP/SL automatique : désactivé",
            "",
        ]
        if not profiles:
            lines.extend(
                [
                    "Aucun profil simulé configuré.",
                    "Commande: `/smartcopy <nom> <wallet_cible> <portfolio_usdc> [mon_wallet]`",
                ]
            )
            return "\n".join(lines)

        lines.append("*Associations retenues:*")
        for profile in profiles.values():
            lines.append(
                f"- `{profile.get('assigned_wallet') or 'auto'}` → `{profile.get('wallet')}` "
                f"({profile.get('name')}, ${float(profile.get('portfolio_amount', 0) or 0):.2f})"
            )
        return "\n".join(lines)
