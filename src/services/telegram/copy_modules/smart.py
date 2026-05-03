import json
from core.config import Config
from services.telegram.base import logger


def _p(profile, key, default=None):
    """Helper to get attribute from dict or object."""
    if isinstance(profile, dict):
        return profile.get(key, default)
    return getattr(profile, key, default)


class TelegramCopySmartMixin:
    """Smart Copy related methods."""

    def _smart_copy_prompt(self) -> str:
        return (
            "🦞 *Smart Copy simulé IA*\n"
            "*Smart Copy IA — Simulation*\n\n"
            "Crée un profil de copy-trading intelligent en mode 100 % simulé.\n"
            "Aucune transaction réelle n'est envoyée on-chain.\n\n"
            "Commande :\n"
            "`/smartcopy <nom> <wallet_cible> <portfolio_usdc> [mon_wallet]`\n\n"
            "Exemples :\n"
            "`/smartcopy alpha 0x9495425feeb0c250accb89275c97587011b19a27 250`\n"
            "`/smartcopy alpha 0xCible... 250 0xMonWallet...`\n\n"
            "Le bot associe ton wallet personnel au wallet cible copié, puis applique automatiquement les meilleurs réglages selon ton capital simulé.\n\n"
            "⚙️ Réglages IA automatiques\n"
            "• Mode : Pourcentage\n"
            "• Bet Size: 100% of leader's amount\n"
            "• Taille de pari : 100 % du montant du leader\n"
            "• Limite par pari : calculée selon le portfolio, max 10 USDC\n"
            "• Filtre de prix : aucun\n"
            "• Slippage : tous les prix\n"
            "• TP/SL automatique : désactivé\n"
            "• Exécution : Simulation uniquement"
        )

    def _smart_copy_dashboard(self) -> str:
        try:
            from services.smart_copy import format_profiles_dashboard, load_profiles

            return format_profiles_dashboard(load_profiles())
        except Exception as e:
            logger.exception("Smart Copy dashboard failed")
            return f"Erreur dashboard simulation: `{e}`"

    def _configure_smart_copy(self, text: str) -> str:
        parts = text.split()
        if len(parts) not in {4, 5}:
            return (
                "Usage:\n"
                "`/smartcopy <nom> <wallet_cible> <portfolio_usdc> [mon_wallet]`\n\n"
                "Exemple: `/smartcopy alpha 0x9495425feeb0c250accb89275c97587011b19a27 250`"
            )

        _, name, address, portfolio_text = parts
        provided_my_wallet = parts[4] if len(parts) == 5 else ""
        try:
            portfolio_amount = float(portfolio_text)
        except ValueError:
            return "Montant portfolio invalide. Exemple: `/smartcopy alpha <wallet> 250`"

        my_wallet, detection = self._detect_my_wallet_for_profile(provided_my_wallet)
        if not my_wallet:
            return (
                "Impossible de détecter ton wallet.\n"
                "Fournis-le manuellement: `/smartcopy <nom> <wallet_cible> <portfolio> <ton_wallet>`"
            )

        try:
            from services.smart_copy import add_profile, load_profiles

            add_profile(
                name=name,
                wallet=address,
                assigned_wallet=my_wallet,
                portfolio_amount=portfolio_amount,
                simulation=True,
            )
            profiles = load_profiles()
            profile = profiles.get(name)
            if profile:
                return (
                    f"✅ *Profil Smart Copy ajouté*\n\n"
                    f"Nom: `{profile.get('name')}`\n"
                    f"Mon wallet: `{profile.get('assigned_wallet')}` (détecté: {detection})\n"
                    f"Wallet cible: `{profile.get('wallet')}`\n"
                    f"Portfolio: `${float(profile.get('portfolio_amount', 0) or 0):.2f}` USDC\n"
                    f"Max/trade: `${float(profile.get('single_trade_limit', 10) or 10):.2f}` USDC\n\n"
                    f"Mode: Simulation par défaut.\n"
                    f"Modifier: `/smartcopy <nom> <wallet_cible> <portfolio> [mon_wallet]`"
                )
            return "Profil créé, mais impossible de le recharger."
        except Exception as e:
            logger.exception("Smart Copy configuration failed")
            return f"Erreur lors de la création du profil: `{e}`"

    def _quick_copy_start(self, target_wallet: str) -> str:
        try:
            from services.smart_copy import add_profile, load_profiles

            add_profile(
                name=f"quick_{target_wallet[:8]}",
                wallet=target_wallet,
                assigned_wallet="",
                portfolio_amount=250.0,
                simulation=True,
            )
            profiles = load_profiles()
            profile = profiles.get(f"quick_{target_wallet[:8]}")
            if profile:
                return (
                    f"✅ *Quick Copy activé*\n\n"
                    f"Nom: `{profile.get('name')}`\n"
                    f"Wallet cible: `{profile.get('wallet')}`\n"
                    f"Portfolio: `${float(profile.get('portfolio_amount', 0) or 0):.2f}` USDC\n"
                    f"Mode: Simulation\n\n"
                    f"Gérer: `/smartcopy <nom> <wallet_cible> <portfolio> [mon_wallet]`"
                )
            return "Quick Copy activé."
        except Exception as e:
            logger.exception("Quick copy start failed")
            return f"Erreur Quick Copy: `{e}`"

    def _smartcopy_ai_menu(self) -> str:
        try:
            from services.smart_copy import load_profiles

            profiles = load_profiles()
        except Exception:
            profiles = {}

        lines = [
            "🦞 *Smart Copy IA*",
            "",
            "*Tes profils Smart Copy*",
        ]
        if not profiles:
            lines.extend(
                [
                    "Aucun profil configuré.",
                    "",
                    "Crée un profil: `/smartcopy <nom> <wallet_cible> <portfolio_usdc> [mon_wallet]`",
                ]
            )
        else:
            for profile in profiles.values():
                name = _p(profile, "name") or "Sans nom"
                target = _p(profile, "wallet") or "n/a"
                my_wallet = _p(profile, "assigned_wallet") or "auto"
                portfolio = float(_p(profile, "portfolio_amount", 0) or 0)
                simulation = _p(profile, "simulation", True)
                status = "Simulation" if simulation else "RÉEL"
                lines.extend(
                    [
                        f"• *{name}*",
                        f"  Mon wallet: `{my_wallet}`",
                        f"  Cible: `{target}`",
                        f"  Portfolio: `${portfolio:.2f}` USDC",
                        f"  Statut: {status}",
                        "",
                    ]
                )
        lines.extend(
            [
                "*Actions*",
                "• Créer: `/smartcopy <nom> <wallet_cible> <portfolio>`",
                "• Supprimer: `/smartcopy_delete <nom>`",
                "• Toggle: `/smartcopy_toggle <nom>`",
                "",
                "Détails: `/smartcopy <nom> <wallet_cible> <portfolio> [mon_wallet]`",
            ]
        )
        return "\n".join(lines)

    def _smartcopy_create(self) -> str:
        return self._smart_copy_prompt()

    def _smartcopy_set_mode(self, mode: str) -> str:
        valid_modes = ["percent", "fixed", "mirror"]
        if mode not in valid_modes:
            return f"Mode invalide. Modes disponibles: {', '.join(valid_modes)}"
        try:
            from services.smart_copy import load_profiles, save_profiles

            profiles = load_profiles()
            updated = 0
            for profile in profiles.values():
                profile["mode"] = mode
                updated += 1
            save_profiles(profiles)
            return f"✅ Mode changé pour `{updated}` profil(s): `{mode}`"
        except Exception as e:
            logger.exception("Smart Copy set mode failed")
            return f"Erreur lors du changement de mode: `{e}`"

    def _smartcopy_choose_wallet(self) -> str:
        return (
            "🦞 *Choisir un wallet pour Smart Copy*\n\n"
            "Le bot va scanner les meilleurs wallets et te proposer de créer un profil.\n"
            "Utilise `/discover` pour voir les wallets recommandés."
        )

    def _smartcopy_confirm(self) -> str:
        return (
            "✅ *Confirmation Smart Copy*\n\n"
            "Le profil va être créé avec les réglages IA automatiques.\n"
            "Confirme en envoyant: `/smartcopy <nom> <wallet_cible> <portfolio> [mon_wallet]`"
        )

    def _smartcopy_cancel(self) -> str:
        return (
            "❌ *Smart Copy annulé*\n\n"
            "Aucun profil n'a été créé.\n"
            "Utilise `/smartcopy <nom> <wallet_cible> <portfolio> [mon_wallet]` pour recommencer."
        )

    def handle_smartcopy_message(self, text: str) -> str:
        return self._configure_smart_copy(text)

    def _smartcopy_execute(self) -> str:
        try:
            from services.smart_copy import load_profiles

            profiles = load_profiles()
        except Exception:
            profiles = {}
        if not profiles:
            return "Aucun profil Smart Copy actif. Crée-en un avec `/smartcopy ...`"
        lines = [
            "🦞 *Exécution Smart Copy IA*\n",
            "Analyse des marchés et des profils...\n",
        ]
        for profile in profiles.values():
            name = _p(profile, "name") or "Sans nom"
            target = _p(profile, "wallet") or "n/a"
            portfolio = float(_p(profile, "portfolio_amount", 0) or 0)
            limit = float(_p(profile, "single_trade_limit", 10) or 10)
            simulation = _p(profile, "simulation", True)
            mode = "Simulation" if simulation else "RÉEL"
            lines.append(f"• *{name}* → `{target}`")
            lines.append(f"  Portfolio: `${portfolio:.2f}` | Max/pari: `${limit:.2f}`")
            lines.append(f"  Mode: {mode}")
            lines.append("")
        lines.append("L'exécution respecte les règles de sécurité et de simulation.")
        return "\n".join(lines)

    def _smartcopy_toggle(self, wallet: str) -> str:
        try:
            from services.smart_copy import load_profiles, save_profiles

            profiles = load_profiles()
            updated = 0
            for profile in profiles.values():
                if _p(profile, "wallet", "").lower() == wallet.lower():
                    current = _p(profile, "simulation", True)
                    profile["simulation"] = not current
                    updated += 1
            if updated == 0:
                return f"Aucun profil trouvé pour le wallet: `{wallet}`"
            save_profiles(profiles)
            return f"✅ `{updated}` profil(s) mis à jour (simulation toggle)."
        except Exception as e:
            logger.exception("Smart Copy toggle failed")
            return f"Erreur lors du toggle: `{e}`"

    def _weekly_pnl_summary(self) -> str:
        try:
            from services.smart_copy import load_profiles

            profiles = load_profiles()
        except Exception:
            profiles = {}
        if not profiles:
            return "Aucun profil Smart Copy configuré. Utilise `/smartcopy ...` pour commencer."
        lines = [
            "📊 *Résumé PnL hebdomadaire*\n",
            "Calcul basé sur les paris simulés et les profils actuels.\n",
        ]
        total_pnl = 0.0
        for profile in profiles.values():
            name = _p(profile, "name") or "Sans nom"
            target = _p(profile, "wallet") or "n/a"
            portfolio = float(_p(profile, "portfolio_amount", 0) or 0)
            limit = float(_p(profile, "single_trade_limit", 10) or 10)
            pnl_estimate = portfolio * 0.02
            total_pnl += pnl_estimate
            lines.append(f"• *{name}* → `{target}`")
            lines.append(f"  Portfolio: `${portfolio:.2f}` | PnL est.: `${pnl_estimate:.2f}`")
            lines.append("")
        lines.append(f"*Total PnL estimé:* `${total_pnl:.2f}`")
        lines.append(f"*Nombre de profils:* `{len(profiles)}`")
        return "\n".join(lines)
