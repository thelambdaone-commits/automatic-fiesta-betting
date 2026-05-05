from .base import *


class TelegramActivityMixin:
    def autopilot_text(self) -> str:
        return "*🦞 AutoPilot*\n\nAucune stratégie active pour le moment."

    def scan_wallet_text(self) -> str:
        return (
            "*🔎 Scan Wallet*\n"
            "*Scanner Wallet*\n\n"
            "Envoie `/scan <wallet>` ou `/scan @profil` avec n'importe quel wallet EVM ou profil Polymarket.\n\n"
            "Exemples :\n"
            "`/scan 0xe8dd7741ccb12350957ec71e9ee332e0d1e6ec86`\n"
            "`/scan @surfandturf`"
        )

    def wallet_search_text(self) -> str:
        return (
            "*🔍 Wallet Search*\n"
            "*Rechercher Wallet*\n\n"
            "Trouve des wallets à analyser, classer, scanner ou copier.\n"
            "Utilise Top 1 %, Meilleurs wallets, Découvrir, ou envoie `/scan <wallet>` ou `/scan @profil` directement."
        )

    def help_text(self) -> str:
        return (
            "*🩺 Help*\n\n"
            "*Commandes principales:*\n"
            "• `/menu` - ouvrir l'accueil\n"
            "• `/top`, `/top20`, `/top50`, `/top themes` - top wallets\n"
            "• `/scan <wallet|@profil>` - analyser un wallet\n"
            "• `/mirror <wallet|@profil>` - ajouter une cible à copier\n"
            "• `/smartcopy <nom> <wallet|@profil> <portfolio_usdc> [mon_wallet]` - créer une paire Smart Copy simulée\n"
            "• `/newwallet` - générer un nouveau signer ETH/POL pour Polymarket\n"
            "• `/bet BUY|SELL <token_id> <montant>` - pari manuel simulé\n"
            "• `/status` - vérifier la configuration\n\n"
            "*Rappels sécurité:*\n"
            "• Le bot tourne en simulation forcée si `SIMULATION_MODE=true` ou `LIVE_TRADING=false`.\n"
            "• Les paires de copytrading sont visibles dans `🪞 Copier` → `🔗 Mes paires`.\n"
            "• Les risques restent disponibles depuis les écrans métier, mais ne sont plus sur l'accueil."
        )

    def _active_trades_text(self) -> str:
        return (
            "*📊 Paris en cours*\n\n"
            "Aucun pari en cours.\n\n"
            "Les paris copiés apparaîtront ici."
        )
    
    def _trade_history_text(self) -> str:
        return (
            "*📜 Historique Copyparis*\n\n"
            "Aucun historique disponible.\n\n"
            "L'historique s'affichera après les premiers paris."
        )
    
    def _discover_smart_wallets(self) -> str:
        """Découvre les smart wallets via Polymarket Analytics et Groq IA"""
        try:
            from services.polymarket_analytics import discover_smart_wallets
            
            # 1. Découverte
            wallets = discover_smart_wallets(limit=1000)
            
            if not wallets:
                return "Aucun wallet découvert. Vérifiez Polymarket Analytics."
            
            # 2. Formatage pour l'IA
            analysis_wallet_data = []
            for w in wallets[:25]:  # Top 25 pour l'IA
                analysis_wallet_data.append({
                    "wallet": w["wallet"],
                    "pnl": w["pnl"],
                    "win_rate": w.get("win_rate", 0),
                    "volume": w.get("volume", 0),
                })
            
            # 3. Analyse IA
            from services.groq_advisor import GroqAdvisor
            analysis = GroqAdvisor().analyze_wallets_from_data(analysis_wallet_data)
            
            # 4. Sauvegarde des wallets recommandés
            self._save_recommended_wallets(wallets[:1000])
            
            return f"Découverte terminée : {len(wallets)} wallets disponibles via l API.\n\n{analysis}\n\nTop {min(len(wallets), 1000)} sauvegardés pour Wallet Mirror."
            
        except Exception as e:
            logger.exception("Error in wallet discovery")
            return f"Erreur: {str(e)}"
    
    def _save_recommended_wallets(self, wallets: list):
        """Sauvegarde les wallets recommandés pour le copy trading"""
        try:
            import json
            from pathlib import Path
            output = Config.CONFIG_DIR / "targets" / "discovered_wallets.json"
            with open(output, "w") as f:
                mirror_wallets = [w["wallet"] for w in wallets]
                json.dump({"wallet_mirror_wallets": mirror_wallets, "copytrade_wallets": mirror_wallets}, f, indent=2)
            logger.info(f"Saved recommended wallets to {output}")
        except Exception as e:
            logger.error(f"Failed to save wallets: {e}")

    def _ia_analysis_text(self) -> str:
        """IA analysis: score wallets, explain why copy or avoid, detect risks"""
        try:
            from services.polymarket_analytics import fetch_top_wallets
            from services.groq_advisor import GroqAdvisor
            
            # Fetch top wallets
            wallets = fetch_top_wallets(limit=10, window="all")
            if not wallets:
                return "Aucun wallet trouvé pour l'analyse IA."
            
            # Prepare data for IA
            wallet_data = []
            for w in wallets[:5]:
                wallet_data.append({
                    "wallet": w.get("wallet"),
                    "username": w.get("username"),
                    "pnl": w.get("pnl", 0),
                    "volume": w.get("volume", 0),
                })
            
            # IA analysis
            analysis = GroqAdvisor().analyze_wallets_from_data(wallet_data)
            return f"*🧠 Analyse IA*\n\n{analysis}\n\nL'IA filtre slippage, liquidité, timing et frais cachés."
            
        except Exception as e:
            logger.warning("IA analysis failed: %s", e)
            return f"Analyse IA indisponible : {e}"

    def _whale_activity_text(self) -> str:
        """Affiche les trades récents des top whales"""
        try:
            from services.whale_activity import get_recent_whale_trades, format_whale_activity_for_telegram
            
            self._whale_trades = get_recent_whale_trades(top_n=10, activity_limit=5)
            self._whale_page = 0
            return format_whale_activity_for_telegram(self._whale_trades, page=self._whale_page, page_size=2)
            
        except Exception as e:
            logger.error(f"Error fetching whale activity: {e}")
            return f"Erreur lors de la récupération des trades whales: {e}"

    def _format_whale_activity_current_page(self) -> str:
        try:
            from services.whale_activity import format_whale_activity_for_telegram

            return format_whale_activity_for_telegram(self._whale_trades, page=self._whale_page, page_size=2)
        except Exception as e:
            logger.error("Error formatting whale activity page: %s", e)
            return f"Erreur activité baleines : {e}"

    def _scan_wallet_prompt(self) -> str:
        """Prompt to ask user for wallet address to scan"""
        return (
            "*🔍 Scanner un Wallet*\n\n"
            "Envoie l'adresse du wallet ou le profil Polymarket à scanner.\n"
            "Exemples: `0x9495425feeb0c250accb89275c97587011b19a27`, `@surfandturf`\n\n"
            "Ou utilisez /scan <wallet> directement."
        )
