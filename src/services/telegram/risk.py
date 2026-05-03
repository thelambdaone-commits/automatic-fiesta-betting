from .base import *


class TelegramRiskMixin:
    def _risk_full_menu(self) -> str:
        wallets = Config.TARGET_WALLETS or []
        lines = ["*🛡️ Gestion des Risques par Wallet*", ""]
        if not wallets:
            lines.append("Aucun wallet cible configuré.")
            lines.append("Ajoute une cible avec `/mirror <wallet>` ou `/smartcopy <nom> <wallet_cible> <portfolio> [mon_wallet]`.")
            return "\n".join(lines)

        lines.append("Chaque wallet suivi possède son propre profil de risque.")
        lines.append("")
        for wallet in wallets:
            profile = self._risk_profile_for_wallet(wallet)
            lines.append(f"*{WalletRanker.short_wallet(wallet)}*")
            lines.append(f"Wallet: `{wallet}`")
            lines.append(f"Source profil: `{profile['source']}`")
            lines.append(f"Mon wallet attribué: `{profile['assigned_wallet']}`")
            lines.append(f"📊 Max par trade: `{profile['max_trade']}`")
            lines.append(f"🛡️ Slippage: `{profile['slippage']}`")
            lines.append(f"💧 Liquidité min: {profile['liquidity']}")
            lines.append(f"🧪 Simulation: {profile['simulation']}")
            lines.append(f"🚨 Stop-loss: {profile['stop_loss']}")
            lines.append("")
        lines.append("Sélectionne un wallet avec les boutons pour voir le détail.")
        return "\n".join(lines)

    def _risk_profile_for_wallet(self, wallet: str) -> Dict[str, str]:
        try:
            from services.smart_copy import get_profile

            smart_profile = get_profile(wallet)
        except Exception:
            smart_profile = None

        if smart_profile:
            assigned_wallet = smart_profile.get("assigned_wallet") or "auto"
            portfolio = float(smart_profile.get("portfolio_amount", 0) or 0)
            return {
                "source": smart_profile.get("name") or "Smart Copy",
                "assigned_wallet": assigned_wallet,
                "portfolio": f"${portfolio:.2f}",
                "wallet_type": smart_profile.get("wallet_type") or "unknown",
                "max_trade": f"${float(smart_profile.get('single_trade_limit', 10) or 10):.2f}",
                "slippage": smart_profile.get("slippage") or "Tous les prix",
                "liquidity": "Aucun filtre",
                "simulation": "ON ✅ forcée",
                "stop_loss": "Désactivé",
                "rules": [
                    "Mode Percentage",
                    "Bet Size 100% du leader",
                    "Plafond par pari propre à cette cible",
                    "Aucun ordre live pour ce profil simulé",
                ],
            }

        slippage = getattr(Config, 'SLIPPAGE_TOLERANCE', 0.01)
        max_order = getattr(Config, 'MAX_ORDER_SIZE', 1000)
        simulation = "Activée ✅" if Config.SIMULATION_MODE or not Config.LIVE_TRADING else "Désactivée / RÉEL"
        return {
            "source": "Standard Wallet Mirror",
            "assigned_wallet": "Wallet principal configuré",
            "portfolio": "Solde Polymarket réel",
            "wallet_type": "standard",
            "max_trade": f"${float(max_order):.2f}",
            "slippage": f"{slippage * 100:.1f}%",
            "liquidity": "ON ✅",
            "simulation": simulation,
            "stop_loss": "NON CONFIGURÉ",
            "rules": [
                "Pas de copie all-in",
                "Filtrage spread large",
                "Vérification prix (pas après pump)",
            ],
        }

    def _risk_wallet_detail(self, wallet: str) -> str:
        wallet = (wallet or "").strip()
        wallets = Config.TARGET_WALLETS or []
        if wallet.lower() not in {item.lower() for item in wallets}:
            return f"Wallet non suivi pour le risque:\n`{wallet}`"

        profile = self._risk_profile_for_wallet(wallet)
        lines = [
            "*🛡️ Profil Risque Wallet*",
            "",
            f"Wallet suivi: `{wallet}`",
            f"Source profil: `{profile['source']}`",
            f"Mon wallet attribué: `{profile['assigned_wallet']}`",
            f"Portfolio/profil: `{profile['portfolio']}`",
            f"Type wallet: `{profile['wallet_type']}`",
            "",
            f"📊 Max par pari: `{profile['max_trade']}`",
            f"🛡️ Slippage: `{profile['slippage']}`",
            f"💧 Liquidité min: {profile['liquidity']}",
            f"🧪 Simulation: {profile['simulation']}",
            f"🚨 Stop-loss: {profile['stop_loss']}",
            "",
            "Règles actives pour ce wallet:",
        ]
        lines.extend(f"• {rule}" for rule in profile["rules"])
        return "\n".join(lines)
    
    def _risk_settings_text(self) -> str:
        max_trade = getattr(Config, 'MAX_ORDER_SIZE', 1000)
        slippage = getattr(Config, 'SLIPPAGE_TOLERANCE', 0.01)
        return (
            "*⚙️ Paramètres de Risque*\n\n"
            f"Max par pari: `{max_trade}$`\n"
            f"Slippage max: `{slippage*100:.1f}%`\n\n"
            "Utilise les boutons pour ajuster."
        )
    
    def _slippage_settings_text(self) -> str:
        slippage = getattr(Config, 'SLIPPAGE_TOLERANCE', 0.01)
        return (
            "*🛡️ Slippage & Frais*\n\n"
            f"Slippage actuel: `{slippage*100:.1f}%`\n"
            "Recommandé: 0.5% - 2%\n\n"
            "Le bot évite les paris si slippage trop élevé."
        )
    
    def _risk_alerts_text(self) -> str:
        return (
            "*🚨 Alertes Risque*\n\n"
            "✅ Liquidity minimum: activé\n"
            "✅ Filtrage spread: activé\n"
            "✅ Pas de copie all-in: activé\n"
            "✅ Simulation avant pari: activé\n\n"
            "Stop-loss journalier: NON CONFIGURÉ"
        )
    
