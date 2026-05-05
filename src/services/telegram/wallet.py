from .base import *


class TelegramWalletMixin:
    def _my_wallet_full(self) -> str:
        """Affiche les wallets signer/proxy et leurs soldes utiles."""
        signer_address = None
        proxy_wallet = None
        native_balance = None
        polymarket_balance = None
        allowance = None
        errors = []

        try:
            from eth_account import Account

            signer_address = Account.from_key(Config.PRIVATE_KEY).address if Config.PRIVATE_KEY else None
        except Exception as e:
            errors.append(f"wallet signer indisponible: {e}")

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
                        proxy_wallet = profile.get("proxyWallet") or profile.get("proxy_wallet")
            except Exception as e:
                errors.append(f"proxy Polymarket non récupéré: {e}")

            try:
                from web3 import Web3

                web3 = Web3(Web3.HTTPProvider(Config.RPC_URL, request_kwargs={"timeout": self.request_timeout}))
                wei_balance = web3.eth.get_balance(signer_address)
                native_balance = float(web3.from_wei(wei_balance, "ether"))
            except Exception as e:
                errors.append(f"solde POL natif non récupéré: {e}")

        proxy_wallet = proxy_wallet or signer_address

        try:
            from services.copy_trade import PolymarketTrader

            trader = PolymarketTrader(mode="prod")
            balance_info = trader.check_cash_balance()
            if balance_info:
                polymarket_balance = float(balance_info.get("balance", 0) or 0)
                allowance = float(balance_info.get("allowance", 0) or 0)
        except Exception as e:
            errors.append(f"solde Polymarket non récupéré: {e}")

        lines = ["*🧬 Mes wallets*", ""]

        lines.extend(
            [
                "*🔐 Wallet signer ETH/POL*",
                "Adresse qui signe les ordres et paie le gas Polygon:",
                f"`{signer_address or 'non configure'}`",
            ]
        )
        if signer_address:
            lines.append(f"⛓️ Blockchain: https://polygonscan.com/address/{signer_address}")
        lines.append(f"Solde natif POL/MATIC: `{native_balance:.6f}`" if native_balance is not None else "Solde natif POL/MATIC: `N/A`")

        lines.extend(
            [
                "",
                "*🏛️ Wallet proxy Polymarket*",
                "Adresse utilisée par Polymarket pour les positions et le solde USDC:",
                f"`{proxy_wallet or 'non detecte'}`",
            ]
        )
        if proxy_wallet:
            lines.append(f"🔗 Polymarket: https://polymarket.com/profile/{proxy_wallet}")
            lines.append(f"📊 Polyanalytics: https://polyanalytics.com/address/{proxy_wallet}")
            lines.append(f"⛓️ Blockchain: https://polygonscan.com/address/{proxy_wallet}")
        lines.append(
            f"Solde Polymarket USDC: `{polymarket_balance:,.2f} USDC`"
            if polymarket_balance is not None
            else "Solde Polymarket USDC: `N/A`"
        )
        if allowance is not None:
            lines.append(f"Allowance CLOB: `{allowance:,.2f}`")

        lines.extend(
            [
                "",
                "*📌 Différence importante*",
                "• Wallet signer ETH/POL = clé privée locale, signature et gas.",
                "• Wallet proxy Polymarket = solde USDC/positions sur Polymarket.",
                "",
                "Les deux adresses ci-dessus sont copiables en appuyant dessus.",
            ]
        )
        if errors:
            lines.append("")
            lines.append("_Infos partielles: certains soldes peuvent être indisponibles si RPC/API répond mal._")

        return "\n".join(lines)

    def my_wallet_keyboard(self) -> dict:
        return {
            "inline_keyboard": [
                [
                    {"text": "🆕 Nouveau wallet", "callback_data": "wallet_create_prompt"},
                    {"text": "🔄 Actualiser", "callback_data": "my_wallet_full"},
                ],
                [
                    {"text": "🔗 CopyBet", "callback_data": "menu:copy_trading"},
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        }

    def _wallet_create_prompt(self) -> str:
        return (
            "*🆕 Nouveau wallet Polymarket*\n\n"
            "Cette action va générer un nouveau *Wallet signer ETH/POL*, dériver ses credentials CLOB, "
            "puis l'activer dans `config/session/default.json`.\n\n"
            "*Ce que tu obtiens:*\n"
            "• 🔐 Signer ETH/POL: nouvelle clé privée locale pour signer les ordres et payer le gas.\n"
            "• 🏛️ Proxy Polymarket: détecté si Polymarket l'expose déjà; sinon le signer est utilisé en mode EOA au départ.\n\n"
            "Le bot sauvegarde l'ancienne session puis redémarre le copy-trade pour charger le nouveau wallet."
        )

    @staticmethod
    def wallet_create_confirm_keyboard() -> dict:
        return {
            "inline_keyboard": [
                [{"text": "✅ Créer + activer", "callback_data": "wallet_create_confirm"}],
                [{"text": "⬅️ Annuler", "callback_data": "my_wallet_full"}],
            ]
        }

    def _wallet_create_confirm(self) -> str:
        try:
            from services.polymarket_wallet_manager import (
                create_and_activate_wallet,
                restart_copy_trade_process,
                short_address,
            )

            result = create_and_activate_wallet()
            restart = restart_copy_trade_process()
            signer = result["signer_address"]
            proxy = result["proxy_wallet"]
            proxy_status = result["proxy_status"]
            backup = result.get("backup_path") or "aucune"
            restart_text = (
                f"Copy-trade redémarré: PID `{restart.get('pid')}`"
                if restart.get("ok")
                else f"Copy-trade à vérifier: {restart.get('error') or 'statut inconnu'}"
            )
            same_wallet = signer.lower() == proxy.lower()
            proxy_line = (
                "Proxy non encore distinct détecté: mode EOA actif."
                if same_wallet or proxy_status == "not_detected"
                else f"Proxy détecté: `{proxy}`"
            )

            return (
                "✅ *Nouveau wallet actif*\n\n"
                "*🔐 Wallet signer ETH/POL*\n"
                f"`{signer}`\n"
                f"Polygonscan: https://polygonscan.com/address/{signer}\n\n"
                "*🏛️ Wallet proxy Polymarket*\n"
                f"`{proxy}`\n"
                f"{proxy_line}\n"
                f"Polymarket: https://polymarket.com/profile/{proxy}\n\n"
                "*Credentials CLOB*\n"
                f"API Key: `{short_address(result.get('api_key'))}`\n"
                "Secret/passphrase: enregistrés dans la session.\n\n"
                f"Sauvegarde ancienne session: `{backup}`\n\n"
                f"{restart_text}"
            )
        except Exception as e:
            logger.exception("Wallet creation failed")
            return f"❌ Création du wallet impossible: `{e}`"
    
    def _check_balance(self) -> str:
        try:
            from services.copy_trade import PolymarketTrader
            trader = PolymarketTrader(mode='prod')
            balance_info = trader.check_cash_balance()
            if balance_info:
                balance = float(balance_info.get('balance', 0))
                return f"*💰 Solde Polymarket*\n\nSolde USDC: `{balance:.2f}$`"
            return "Impossible de récupérer le solde."
        except Exception as e:
            return f"Erreur: {str(e)}"
    
