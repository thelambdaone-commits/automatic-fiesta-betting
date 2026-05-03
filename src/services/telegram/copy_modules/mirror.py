from core.config import Config
from services.telegram.base import logger


def _p(profile, key, default=None):
    """Helper to get attribute from dict or object."""
    if isinstance(profile, dict):
        return profile.get(key, default)
    return getattr(profile, key, default)


class TelegramCopyMirrorMixin:
    """Mirror wallet copy trading methods."""

    def _wallet_mirror_status(self) -> str:
        wallets = Config.TARGET_WALLETS or []
        if not wallets:
            return "Wallet Mirror actif, mais aucun wallet cible n'est configuré. Utilise `/mirror <wallet>`."

        lines = [
            "*🪞 Copier un Wallet*",
            "",
            "Wallets suivis pour copy trading:",
        ]
        for wallet in wallets:
            short = f"{wallet[:6]}...{wallet[-4:]}" if len(wallet) >= 10 else wallet
            lines.append(f"- `{wallet}` ({short})")
            lines.append(f"  🔗 Polymarket: https://polymarket.com/profile/{wallet}")
            lines.append(f"  📊 Polyanalytics: https://polyanalytics.com/address/{wallet}")
            lines.append(f"  ⛓️ Blockchain: https://polygonscan.com/address/{wallet}")
        try:
            from services.smart_copy import load_profiles

            profiles = load_profiles()
            if profiles:
                lines.append("")
                lines.append("*Profils Smart Copy simulés:*")
                for profile in profiles.values():
                    assigned = profile.get("assigned_wallet") or "auto"
                    lines.append(
                        f"- `{profile.get('name')}`"
                        f"\n  Mon wallet: `{assigned}`"
                        f"\n  Cible: `{profile.get('wallet')}`"
                        f"\n  Portfolio: `${float(profile.get('portfolio_amount', 0) or 0):.2f}`"
                        f" | max/trade `${float(profile.get('single_trade_limit', 10) or 10):.2f}`"
                    )
        except Exception as e:
            logger.debug("Unable to load Smart Copy profiles: %s", e)
        lines.append("")
        mode = "SIMULATION" if Config.SIMULATION_MODE or not Config.LIVE_TRADING else "RÉEL"
        lines.append("✅ Copytrading: **ACTIF**" if wallets else "❌ Copytrading: **INACTIF**")
        lines.append(f"Mode exécution: **{mode}**")
        lines.append("")
        lines.append("Commandes: `/scan <wallet>`, `/mirror <wallet>`, `/smartcopy <nom> <wallet_cible> <portfolio> [mon_wallet]`.")
        return "\n".join(lines)

    @staticmethod
    def _configured_signer_wallet() -> str:
        try:
            from eth_account import Account

            return Account.from_key(Config.PRIVATE_KEY).address if Config.PRIVATE_KEY else ""
        except Exception:
            return ""

    def _copytrade_pairs_text(self) -> str:
        wallets = Config.TARGET_WALLETS or []
        try:
            from services.smart_copy import load_profiles

            profiles = load_profiles()
        except Exception as e:
            logger.debug("Unable to load Smart Copy profiles for pairs: %s", e)
            profiles = {}

        profiles_by_wallet = {
            str(_p(profile, "wallet") or "").lower(): profile
            for profile in profiles.values()
            if _p(profile, "wallet")
        }
        signer_wallet = self._configured_signer_wallet()

        simulation_profiles = []
        live_profiles = []
        for profile in profiles.values():
            if _p(profile, "simulation", True):
                simulation_profiles.append(profile)
            else:
                live_profiles.append(profile)

        lines = [
            "*🔗 Mes paires de copytrading*",
            "",
        ]

        if not wallets and not profiles:
            lines.extend(
                [
                    "Aucune paire configurée.",
                    "Ajoute une cible avec `/mirror <wallet>` ou `/smartcopy <nom> <wallet_cible> <portfolio> [mon_wallet]`.",
                ]
            )
            return "\n".join(lines)

        lines.append("🧪 *Mode SIMULATION*")
        lines.append("")

        sim_count = 0
        displayed_profiles = set()
        for profile in simulation_profiles:
            target_wallet = _p(profile, "wallet") or "n/a"
            displayed_profiles.add(target_wallet.lower())
            my_wallet = _p(profile, "assigned_wallet") or signer_wallet or "auto"
            name = _p(profile, "name") or "Smart Copy"
            wallet_type = _p(profile, "wallet_type") or "Smart Copy"
            portfolio = float(_p(profile, "portfolio_amount", 0) or 0)
            limit = float(_p(profile, "single_trade_limit", 10) or 10)
            lines.extend(
                [
                    "🦞 *Smart Copy IA*",
                    f"• {name}",
                    f"  Cible : `{target_wallet}`",
                    f"  Mon wallet : `{my_wallet}`",
                    f"  Type : `{wallet_type}`",
                    f"  Portfolio : `{portfolio:.2f}` USDC",
                    f"  Max/trade : `{limit:.2f}` USDC",
                    f"  Mode : Pourcentage — 100 %",
                    "  Statut : Simulation",
                    "",
                ]
            )
            sim_count += 1

        if Config.SIMULATION_MODE or not Config.LIVE_TRADING:
            for target_wallet in wallets:
                if target_wallet.lower() not in profiles_by_wallet:
                    my_wallet = signer_wallet or "Wallet principal configuré"
                    lines.extend(
                        [
                            "• *Wallet Mirror*",
                            f"  Mon wallet: `{my_wallet}`",
                            f"  Wallet cible: `{target_wallet}`",
                            "  Type : `Wallet Mirror standard`",
                            f"  Max/trade : `${float(getattr(Config, 'MAX_ORDER_SIZE', 1000)):.2f}` | slippage `{float(getattr(Config, 'SLIPPAGE_TOLERANCE', 0.01)) * 100:.1f}%`",
                            "  Statut : Simulation",
                            "",
                        ]
                    )
                    sim_count += 1

        if sim_count == 0:
            lines.append("Aucun profil en mode simulation.")
            lines.append("")

        lines.append("🔴 *Mode RÉEL*")
        lines.append("")

        live_count = 0
        for profile in live_profiles:
            target_wallet = _p(profile, "wallet") or "n/a"
            displayed_profiles.add(target_wallet.lower())
            my_wallet = _p(profile, "assigned_wallet") or signer_wallet or "auto"
            name = _p(profile, "name") or "Smart Copy"
            wallet_type = _p(profile, "wallet_type") or "Smart Copy"
            portfolio = float(_p(profile, "portfolio_amount", 0) or 0)
            limit = float(_p(profile, "single_trade_limit", 10) or 10)
            lines.extend(
                [
                    "🦞 *Smart Copy IA*",
                    f"• {name}",
                    f"  Cible : `{target_wallet}`",
                    f"  Mon wallet : `{my_wallet}`",
                    f"  Type : `{wallet_type}`",
                    f"  Portfolio : `{portfolio:.2f}` USDC",
                    f"  Max/trade : `{limit:.2f}` USDC",
                    f"  Mode : Pourcentage — 100 %",
                    "  Statut : RÉEL",
                    "",
                ]
            )
            live_count += 1

        if not Config.SIMULATION_MODE and Config.LIVE_TRADING:
            for target_wallet in wallets:
                if target_wallet.lower() not in profiles_by_wallet:
                    my_wallet = signer_wallet or "Wallet principal configuré"
                    lines.extend(
                        [
                            "• *Wallet Mirror*",
                            f"  Mon wallet: `{my_wallet}`",
                            f"  Wallet cible: `{target_wallet}`",
                            "  Type : `Wallet Mirror standard`",
                            f"  Max/trade : `${float(getattr(Config, 'MAX_ORDER_SIZE', 1000)):.2f}` | slippage `{float(getattr(Config, 'SLIPPAGE_TOLERANCE', 0.01)) * 100:.1f}%`",
                            "  Statut : RÉEL",
                            "",
                        ]
                    )
                    live_count += 1

        if live_count == 0:
            lines.append("Aucun profil en mode RÉEL.")
            lines.append("")

        seen_all = set()
        for w in wallets:
            seen_all.add(w.lower())
        orphan_profiles = [
            profile
            for profile in profiles.values()
            if (str(_p(profile, "wallet") or "").lower() not in seen_all)
            and (str(_p(profile, "wallet") or "").lower() not in displayed_profiles)
        ]
        if orphan_profiles:
            lines.append("*Profils Smart Copy non actifs dans Wallet Mirror:*")
            for profile in orphan_profiles:
                target_wallet = _p(profile, "wallet") or "n/a"
                my_wallet = _p(profile, "assigned_wallet") or signer_wallet or "auto"
                status = "Simulation" if _p(profile, "simulation", True) else "RÉEL"
                lines.append(f"- `{my_wallet}` → `{target_wallet}` ({_p(profile, 'name') or 'Smart Copy'}, {status})")

        lines.append("Modifier: `/smartcopy <nom> <wallet_cible> <portfolio_usdc> [mon_wallet]` ou `/mirror <wallet>`.")
        return "\n".join(lines)

    def _mirror_add_prompt(self) -> str:
        return (
            "*➕ Ajouter un wallet à copier*\n\n"
            "Envoie:\n"
            "`/mirror <wallet>`\n\n"
            "Le bot va scanner le wallet, l'ajouter aux cibles, puis le monitor suivra toutes les cibles configurées."
        )

    def _mirror_remove_menu_text(self) -> str:
        wallets = Config.TARGET_WALLETS or []
        if not wallets:
            return "*🗑️ Supprimer wallet*\n\nAucun wallet suivi actuellement."
        return (
            "*🗑️ Supprimer wallet*\n\n"
            "Choisis le wallet à retirer de Wallet Mirror.\n"
            "La suppression met à jour `config/targets/wallets.json`."
        )

    def _toggle_copy_trading(self) -> str:
        mode = "SIMULATION" if Config.SIMULATION_MODE or not Config.LIVE_TRADING else "RÉEL"
        return (
            "*✅ Copytrading*\n\n"
            "État: **ACTIF**\n\n"
            f"Mode exécution: `{mode}`\n\n"
            "Le bot copie les paris des wallets configurés.\n"
            "Utilise `/mirror <wallet>` pour ajouter ou prioriser une cible."
        )

    def _save_wallet_mirror_target(self, address: str):
        targets_file = Config.TARGETS_FILE
        targets_file.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if targets_file.exists():
            with targets_file.open("r", encoding="utf-8") as file:
                data = json.load(file)

        current = data.get("wallet_mirror_wallets") or data.get("copytrade_wallets") or []
        wallets = [wallet for wallet in current if wallet.lower() != address.lower()]
        wallets.insert(0, address)
        data["wallet_mirror_wallets"] = wallets
        data["copytrade_wallets"] = wallets
        data.setdefault("backtest_wallets", wallets)

        with targets_file.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

        Config.TARGET_WALLETS = wallets
        Config.TARGET_WALLET = wallets[0] if wallets else None

    def _remove_wallet_mirror_target(self, address: str) -> str:
        import json
        address = (address or "").strip()
        targets_file = Config.TARGETS_FILE
        data = {}
        if targets_file.exists():
            with targets_file.open("r", encoding="utf-8") as file:
                data = json.load(file)

        current = data.get("wallet_mirror_wallets") or data.get("copytrade_wallets") or []
        wallets = [wallet for wallet in current if wallet.lower() != address.lower()]
        removed = len(wallets) != len(current)

        data["wallet_mirror_wallets"] = wallets
        data["copytrade_wallets"] = wallets
        if "backtest_wallets" in data:
            data["backtest_wallets"] = [wallet for wallet in data.get("backtest_wallets", []) if wallet.lower() != address.lower()]

        targets_file.parent.mkdir(parents=True, exist_ok=True)
        with targets_file.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

        Config.TARGET_WALLETS = wallets
        Config.TARGET_WALLET = wallets[0] if wallets else None

        if not removed:
            return f"Wallet non trouvé dans les cibles:\n`{address}`"
        if not wallets:
            return f"Wallet supprimé:\n`{address}`\n\nAucun wallet cible restant."
        return f"Wallet supprimé:\n`{address}`\n\nWallets restants: `{len(wallets)}`"

    def _detect_my_wallet_for_profile(self, provided_wallet: str = "") -> tuple[str, str]:
        import requests
        provided_wallet = (provided_wallet or "").strip()
        if provided_wallet:
            return provided_wallet, "manuel"

        signer_address = ""
        proxy_wallet = ""
        try:
            from eth_account import Account

            signer_address = Account.from_key(Config.PRIVATE_KEY).address if Config.PRIVATE_KEY else ""
        except Exception as e:
            logger.debug("Signer wallet detection failed: %s", e)

        if signer_address:
            try:
                response = requests.get(
                    f"{Config.GAMMA_API_HOST.rstrip('/')}/public-profile",
                    params={"address": signer_address},
                    timeout=self.request_timeout,
                )
                if response.ok:
                    profile = response.json()
                    if isinstance(profile, dict):
                        proxy_wallet = profile.get("proxyWallet") or profile.get("proxy_wallet") or ""
            except Exception as e:
                logger.debug("Proxy wallet detection failed: %s", e)

        if proxy_wallet:
            return proxy_wallet, "proxy Polymarket auto"
        if signer_address:
            return signer_address, "signer auto"
        return "", "non détecté"
