import logging
import json
from typing import Dict, Optional, Tuple, Union

from core.config import Config
from ..keyboards.main import MainKeyboardMixin
from ..keyboards.copy_betting import CopyBettingKeyboardMixin
from ..keyboards.wallets import WalletsKeyboardMixin
from ..keyboards.discover import DiscoverKeyboardMixin
from ..keyboards.settings import SettingsKeyboardMixin
from ..top_wallets import TelegramTopWalletsMixin
from ..copy_modules.mirror import TelegramCopyMirrorMixin
from ..wallet import TelegramWalletMixin

# Import history_keyboard function
def history_keyboard(page: int = 0, total_pages: int = 1) -> Dict:
    """Wrapper to call CopyBettingKeyboardMixin.history_keyboard."""
    return CopyBettingKeyboardMixin.history_keyboard(page=page, total_trades=total_pages*5, page_size=5)

logger = logging.getLogger(__name__)


class ActionHandler(
    MainKeyboardMixin,
    CopyBettingKeyboardMixin,
    WalletsKeyboardMixin,
    DiscoverKeyboardMixin,
    SettingsKeyboardMixin,
    TelegramTopWalletsMixin,
    TelegramCopyMirrorMixin,
    TelegramWalletMixin,
):
    """Handles all bot actions and callbacks."""
    
    def __init__(self):
        # Initialize all keyboard mixins
        super().__init__()
        self._callbacks = None  # Lazy loaded
        self._user_settings = {}  # Initialize user settings
    
    @property
    def callbacks(self):
        """Lazy load callback handler."""
        if self._callbacks is None:
            from ..callbacks import CallbackHandler
            self._callbacks = CallbackHandler()
        return self._callbacks
    
    def handle_action(self, action: str) -> Union[str, Tuple[str, Dict]]:
        """
        Main action handler.
        Returns either text string or (text, keyboard) tuple.
        """
        action = self._normalize_action(action)

        # New hierarchical menus (format: "menu:xxx")
        if action == "menu":
            return self.home_text(), self.keyboard()
        if action == "menu:copy_trading":
            return "🔗 *Copy Betting*\n\nChoisis une action :", self.copy_trading_keyboard()
        if action == "menu:mes_wallets":
            return self._mes_wallets_text(), self.mes_wallets_keyboard()
        if action == "menu:decouvrir":
            return "🧭 *Découvrir*\n\nTrouve de nouveaux wallets et marchés.", self.decouvrir_keyboard()
        if action == "menu:parametres":
            return self._settings_menu(), self.parametres_keyboard()
        if action == "my_wallet_full":
            return self._my_wallet_full(), self.keyboard()
        
        # Handle specific actions
        if action.startswith("menu:"):
            return self._handle_menu_action(action)
        
        # Legacy actions
        if action == "scan_wallet":
            return self.scan_wallet_text()
        # Handle scan_<wallet_address> actions
        if action.startswith("scan_") and action not in ("scan_wallet", "scan_wallet_prompt"):
            wallet_address = action[5:]
            return self._scan_wallet_result(wallet_address)
        # Handle groq_<wallet_address> actions (IA analysis)
        if action.startswith("groq_") and action != "groq_analyze":
            wallet_address = action[5:]
            return self._handle_groq_wallet(wallet_address), self.decouvrir_keyboard()
        # Handle trades_<wallet_address> actions (wallet trades history)
        if action.startswith("trades_"):
            wallet_address = action[7:]
            return self._handle_trades_wallet(wallet_address), self.decouvrir_keyboard()
        # Handle orders_<wallet_address> actions (wallet orders)
        if action.startswith("orders_"):
            wallet_address = action[7:]
            return self._handle_wallet_orders(wallet_address), self.decouvrir_keyboard()
        # Handle positions_<wallet_address> actions (wallet positions)
        if action.startswith("positions_"):
            wallet_address = action[10:]
            return self._handle_wallet_positions(wallet_address), self.decouvrir_keyboard()
        # Handle quick_copy_<wallet_address> actions
        if action.startswith("quick_copy_"):
            wallet_address = action[11:]
            return self._handle_quick_copy(wallet_address), self.smartcopy_mode_keyboard()
        # Handle mirror_add_<wallet_address> actions
        if action.startswith("mirror_add_"):
            wallet_address = action[11:]
            return self._handle_mirror_add(wallet_address), self.decouvrir_keyboard()
        if action in {"trades_theme", "market_themes"} or action.startswith("theme_"):
            return "📊 *Marchés par thème*\n\nChoisis une catégorie de marchés.", self.paris_theme_keyboard()

        legacy_result = self._handle_legacy_action(action)
        if legacy_result is not None:
            return legacy_result
        
        # Use callback handler for complex actions
        if ":" in action:
            result = self.callbacks.handle(self, action)
            if isinstance(result, tuple):
                return result
            return result, self.keyboard_for_action(action)
        
        return f"⚠️ Action inconnue: {action}"

    @staticmethod
    def _normalize_action(action: str) -> str:
        aliases = {
            "rankwallets": "rank_wallets",
            "rankwallets20": "rank_wallets_20",
            "rankwallets50": "rank_wallets_50",
            "rankwalletsthemes": "rank_wallets_themes",
            "rankthemetop10all": "rank_theme_top10_all",
            "top10": "rank_wallets",
            "top20": "rank_wallets_20",
            "top50": "rank_wallets_50",
        }
        return aliases.get(action, action)

    def _handle_legacy_action(self, action: str) -> Optional[Union[str, Tuple[str, Dict]]]:
        """Handle pre-refactor callback names still used by keyboards."""
        if action == "discover":
            return self.handle_action("menu:decouvrir")
        if action == "settings_menu":
            return self._settings_menu(), self.settings_keyboard()
        if action == "settings_mode":
            return self._settings_mode(), self.settings_keyboard()
        if action == "settings_mode_live":
            return self._settings_mode_live(), self.settings_keyboard()
        if action == "settings_max_trade":
            return self._settings_max_trade(), self.settings_keyboard()
        if action == "settings_slippage":
            return self._settings_slippage(), self.settings_keyboard()
        if action == "settings_notif":
            return self._risk_alerts_text(), self.parametres_keyboard()
        if action == "settings_delete":
            return "🗑️ *Suppression du compte*\n\nAction désactivée par sécurité.", self.parametres_keyboard()
        if action == "my_wallet":
            return self._my_wallet_text(), self.parametres_keyboard()

        if action == "status":
            return self._enhanced_status(), self.keyboard()
        if action == "performance":
            return self._performance_text(), self.performance_keyboard()
        if action == "help":
            return self.help_text(), self.keyboard()
        if action == "autopilot":
            return self.autopilot_text(), self.autopilot_keyboard()
        if action in {"autopilot_start", "autopilot_pause"}:
            return "📡 *AutoPilot*\n\nAction enregistrée en mode simulation.", self.autopilot_keyboard()

        if action == "wallet_mirror":
            return self._wallet_selection_text(), self.wallet_selection_keyboard()
        if action.startswith("select_wallet:"):
            return self._select_wallet(action.split(":", 1)[1]), self.mes_wallets_keyboard()
        if action in {"mirror_add_prompt", "copy_pairs"}:
            if action == "copy_pairs":
                return self._copytrade_pairs_text(), self.mirror_keyboard()
            return self._mirror_add_prompt(), self.mirror_keyboard()
        if action == "mirror_remove_menu":
            return self._mirror_remove_menu_text(), self.mirror_remove_keyboard()
        if action.startswith("mirror_remove_"):
            return self._handle_mirror_remove(action), self.mirror_keyboard()

        if action == "wallet_search":
            return self.wallet_search_text(), self.wallet_search_keyboard()
        if action == "manual_trade":
            if not self._active_wallet():
                return (
                    "⚠️ *Aucun wallet actif*\n\n"
                    "Sélectionne un wallet avant d'effectuer un pari.",
                    self.mes_wallets_keyboard(),
                )
            return self._manual_trade_text(), self.manual_trade_keyboard()
        if action == "user_wallet_select":
            return self._wallet_selection_text(), self.wallet_selection_keyboard()
        if action == "manual_buy_prompt":
            return self._manual_trade_prompt("BUY"), self.manual_trade_keyboard()
        if action == "manual_sell_prompt":
            return self._manual_trade_prompt("SELL"), self.manual_trade_keyboard()
        if action == "check_balance":
            return self._wallet_balance_text(), self.manual_trade_keyboard()
        if action == "trade_history":
            self._history_page = 0
            return self._wallet_history_text(page=0), history_keyboard(page=0, total_pages=getattr(self, '_history_total_pages', 1))
        if action == "active_trades":
            return self._active_trades_text(), self.trades_keyboard()
        if action == "wallet_orders":
            wallet = self._active_wallet()
            if not wallet: return "⚠️ Aucun wallet actif.", self.mes_wallets_keyboard()
            return self._handle_wallet_orders(wallet), history_keyboard(page=0, total_pages=1)
        if action == "wallet_positions":
            wallet = self._active_wallet()
            if not wallet: return "⚠️ Aucun wallet actif.", self.mes_wallets_keyboard()
            return self._handle_wallet_positions(wallet), history_keyboard(page=0, total_pages=1)
        if action == "performance_mirrors":
            return self._mirrors_performance_text(), self.keyboard()
        if action == "history_next":
            page = getattr(self, '_history_page', 0) + 1
            self._history_page = page
            return self._wallet_history_text(page=page), history_keyboard(page=page, total_pages=getattr(self, '_history_total_pages', 1))
        if action == "history_prev":
            page = max(0, getattr(self, '_history_page', 0) - 1)
            self._history_page = page
            return self._wallet_history_text(page=page), history_keyboard(page=page, total_pages=getattr(self, '_history_total_pages', 1))
        if action == "history_refresh":
            self._history_page = 0
            return self._wallet_history_text(page=0), history_keyboard(page=0, total_pages=getattr(self, '_history_total_pages', 1))

        if action == "scan_wallet_prompt":
            return self._scan_wallet_prompt(), self.decouvrir_keyboard()
        if action == "top_wallets_menu":
            return self._rank_wallets_text("rank_wallets"), self.top_wallets_page_keyboard()
        if action in {"rank_wallets", "rank_wallets_20", "rank_wallets_50"}:
            return self._rank_wallets_text(action), self.top_wallets_page_keyboard()
        if action == "rank_wallets_themes":
            return self._rank_wallets_themes_text(), self.top_wallets_themes_keyboard()
        if action == "rank_theme_top10_all":
            return self._handle_top10_all_themes(), self.top_wallets_top10_all_keyboard()
        if action.startswith("rank_theme_"):
            return self._rank_theme_detail_text(action), self.top_wallets_theme_detail_keyboard()
        if action in {"rank_prev", "rank_next"}:
            return self._rank_page_text(action), self.top_wallets_page_keyboard()
        if action == "rank_close":
            return self.handle_action("menu:decouvrir")
        if action == "whale_activity":
            return self._whale_activity_text(), self.whale_activity_keyboard()
        if action in {"whale_prev", "whale_next"}:
            return self._format_whale_activity_current_page(), self.whale_activity_keyboard()
        if action == "whale_close":
            return self.handle_action("menu:decouvrir")
        if action == "market_search":
            return self._market_search_text(), self.market_search_keyboard()
        if action == "top_markets":
            return self.top_markets_text(), self.top_markets_keyboard()
        if action == "market_themes":
            return "📊 *Marchés par thème*\n\nChoisis une catégorie de marchés.", self.paris_theme_keyboard()
        if action == "ia_analysis":
            return self._ia_analysis_text(), self.decouvrir_keyboard()

        if action == "smartcopy_ai_menu":
            return self._smartcopy_menu_text(), self.smartcopy_ai_menu_keyboard()
        if action == "smartcopy_create":
            return self._smart_copy_prompt(), self.smartcopy_mode_keyboard()
        if action == "smart_copy_dashboard":
            return self._smart_copy_dashboard(), self.smartcopy_dashboard_keyboard()
        if action == "simulate_trade":
            return self._simulate_trade_text(), self.manual_trade_keyboard()
        if action.startswith("smartcopy_"):
            return self._smartcopy_placeholder(action), self.smartcopy_ai_menu_keyboard()

        if action == "risk_menu":
            return self._risk_settings_text(), self.risk_keyboard()
        if action in {"risk_settings", "slippage_settings", "risk_alerts"}:
            if action == "slippage_settings":
                return self._slippage_settings_text(), self.risk_keyboard()
            if action == "risk_alerts":
                return self._risk_alerts_text(), self.risk_keyboard()
            return self._risk_settings_text(), self.risk_keyboard()

        return None

    def _my_wallet_text(self) -> str:
        wallet = getattr(Config, "WALLET_ADDRESS", "") or "Non configuré"
        return f"👛 *Wallet principal*\n\n`{wallet}`"

    @staticmethod
    def _short_wallet(wallet: str) -> str:
        return f"{wallet[:6]}...{wallet[-3:]}" if wallet and len(wallet) >= 12 else (wallet or "")

    def _configured_wallets(self) -> list:
        wallets = list(Config.TARGET_WALLETS or [])
        if wallets:
            return wallets

        targets_file = Config.TARGETS_FILE
        if not targets_file.exists():
            root_targets_file = Config.BASE_DIR / "config" / "targets" / "wallets.json"
            targets_file = root_targets_file if root_targets_file.exists() else targets_file

        try:
            with targets_file.open("r", encoding="utf-8") as file:
                data = json.load(file)
            wallets = data.get("wallet_mirror_wallets") or data.get("copytrade_wallets") or []
        except Exception as exc:
            logger.warning("Failed to load configured wallets: %s", exc)
            wallets = []

        Config.TARGET_WALLETS = wallets
        Config.TARGET_WALLET = wallets[0] if wallets else getattr(Config, "TARGET_WALLET", None)
        return wallets

    def _active_wallet(self) -> str:
        wallet = ((self._user_settings or {}).get("default_wallet") or "").strip()
        if not wallet:
            return ""
        for configured in self._configured_wallets():
            if wallet.lower() == configured.lower():
                return configured
        return ""

    def _active_wallet_line(self) -> str:
        wallet = self._active_wallet()
        if not wallet:
            return "⭐ Wallet actif : Aucun"
        return f"⭐ Wallet actif : `{self._short_wallet(wallet)}`"

    def _mes_wallets_text(self) -> str:
        return "\n".join(
            [
                "🎯 *Mes Mirroirs (Cibles)*",
                "",
                self._active_wallet_line(),
                "",
                "Gérer les wallets que vous copiez automatiquement.",
            ]
        )

    def _wallet_selection_text(self) -> str:
        wallets = self._configured_wallets()
        lines = [
            "🎯 *Mes Mirroirs*",
            "",
            self._active_wallet_line(),
            "",
        ]
        if not wallets:
            lines.append("Aucun wallet suivi actuellement.")
            lines.append("Utilise `➕ Ajouter` pour configurer un wallet.")
        else:
            lines.append("Sélectionne le wallet actif :")
        return "\n".join(lines)

    def _select_wallet(self, wallet: str) -> str:
        wallet = (wallet or "").strip()
        wallets = self._configured_wallets()
        if not any(wallet.lower() == configured.lower() for configured in wallets):
            return "\n".join(
                [
                    "👛 *Mes Wallets*",
                    "",
                    "⚠️ Wallet introuvable dans la liste configurée.",
                    "",
                    self._active_wallet_line(),
                ]
            )

        self._user_settings["default_wallet"] = wallet
        self._save_settings()
        return "\n".join(
            [
                "👛 *Mes Wallets*",
                "",
                f"⭐ Wallet actif : `{self._short_wallet(wallet)}`",
            ]
        )

    def _wallet_balance_text(self) -> str:
        try:
            from services.copy_trade import PolymarketTrader

            trader = PolymarketTrader(mode="test")
            balance_info = trader.check_cash_balance()
            if balance_info:
                return f"💰 *Solde USDC*\n\n`{float(balance_info.get('balance', 0) or 0):.2f}` USDC"
        except Exception as exc:
            logger.warning("Balance check failed: %s", exc)
        return "💰 *Solde USDC*\n\nIndisponible pour le moment."

    def _market_search_text(self) -> str:
        return (
            "*🔎 Recherche de marchés*\n\n"
            "Envoie une recherche avec `/market <mot-clé>` ou utilise les catégories par thème."
        )

    def _smartcopy_menu_text(self) -> str:
        return "*🦞 Smart Copy IA*\n\nCréer, simuler ou consulter tes profils Smart Copy."

    def _smartcopy_placeholder(self, action: str) -> str:
        return f"*🦞 Smart Copy IA*\n\nAction `{action}` prête. Utilise `/smartcopy` pour configurer une stratégie complète."

    def _handle_mirror_remove(self, action: str) -> str:
        wallet = action.replace("mirror_remove_", "", 1)
        if not wallet:
            return "Wallet invalide."
        return f"🗑️ Suppression demandée pour `{wallet[:8]}...{wallet[-6:]}`. Utilise la configuration pour confirmer."

    def _ensure_rank_scores(self, limit: int = 50, with_themes: bool = False) -> bool:
        from services.wallet_ranker import THEME_RANK_LIMIT, WalletRanker

        current = getattr(self, "_rank_scores", []) or []
        if current and len(current) >= limit:
            if not with_themes:
                return True
            ranker = WalletRanker(limit=limit)
            self._rank_scores = current[:limit]
            ranker.enrich_themes(self._rank_scores)
            self._apply_local_activity_themes()
            return True

        ranker = WalletRanker(limit=limit)
        if with_themes:
            self._rank_scores = ranker.rank_by_theme(limit=min(limit, THEME_RANK_LIMIT))
        else:
            self._rank_scores = ranker.rank(limit=limit)
        if with_themes:
            self._apply_local_activity_themes()
        self._rank_page = 0
        return bool(self._rank_scores)

    def _apply_local_activity_themes(self):
        """Infer wallet themes from the local whale activity cache without network fan-out."""
        import json
        from collections import defaultdict
        from services.wallet_ranker import WalletRanker

        activity_file = Config.DATA_DIR / "whale_activity.jsonl"
        if not activity_file.exists():
            return

        rows_by_wallet = defaultdict(list)
        try:
            with activity_file.open("r", encoding="utf-8") as file:
                for line in file:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    wallet = str(row.get("wallet") or "").lower()
                    if wallet:
                        rows_by_wallet[wallet].append(row)
        except Exception as exc:
            logger.warning("Unable to load local whale activity themes: %s", exc)
            return

        ranker = WalletRanker()
        for score in getattr(self, "_rank_scores", []) or []:
            rows = rows_by_wallet.get(str(score.wallet).lower(), [])
            if rows:
                score.theme = ranker.infer_theme(rows)

    def _rank_wallets_text(self, action: str) -> str:
        from services.wallet_ranker import WalletRanker

        display_limit = 10
        if action.endswith("_20"):
            display_limit = 20
        elif action.endswith("_50"):
            display_limit = 50

        self._rank_display_limit = display_limit
        if not self._ensure_rank_scores(limit=display_limit):
            return "Aucun wallet trouvé sur le leaderboard."
        return WalletRanker.format_scores(
            self._rank_scores,
            page=getattr(self, "_rank_page", 0),
            display_limit=display_limit,
        )

    def _rank_wallets_themes_text(self) -> str:
        from services.wallet_ranker import THEME_RANK_LIMIT, WalletRanker

        self._rank_display_limit = THEME_RANK_LIMIT
        if not self._ensure_rank_scores(limit=THEME_RANK_LIMIT, with_themes=True):
            return "Aucun wallet trouvé sur le leaderboard."
        return WalletRanker.format_theme_menu(self._rank_scores)

    def _rank_theme_detail_text(self, action: str) -> str:
        from services.wallet_ranker import THEME_DETAIL_DISPLAY_LIMIT, THEME_RANK_LIMIT, WalletRanker

        if not self._ensure_rank_scores(limit=THEME_RANK_LIMIT, with_themes=True):
            return "Aucun wallet trouvé sur le leaderboard."
        slug = action.replace("rank_theme_", "", 1)
        self._rank_selected_theme = WalletRanker.theme_from_slug(slug)
        return WalletRanker.format_selected_theme_scores(
            self._rank_scores,
            self._rank_selected_theme,
            display_limit=THEME_DETAIL_DISPLAY_LIMIT,
        )

    def _rank_page_text(self, action: str) -> str:
        page = getattr(self, "_rank_page", 0)
        if action == "rank_next":
            page += 1
        elif action == "rank_prev":
            page = max(0, page - 1)
        self._rank_page = page
        display_limit = getattr(self, "_rank_display_limit", 10)
        return self._rank_wallets_text(f"rank_wallets_{display_limit}" if display_limit != 10 else "rank_wallets")
    
    def _handle_menu_action(self, action: str) -> Union[str, Tuple[str, Dict]]:
        """Handle menu:xxx actions."""
        if action == "menu:copy_strategies":
            return self._copytrade_pairs_text(), self.copy_trading_keyboard()
        if action == "menu:copy_add":
            return self._mirror_add_prompt(), self.copy_trading_keyboard()
        if action == "menu:wallet_add":
            return self._mirror_add_prompt(), self.mes_wallets_keyboard()
        if action == "menu:discover_scan":
            return self.scan_wallet_text(), self.decouvrir_keyboard()
        
        return f"⚠️ Action de menu inconnue: {action}"
    
    def keyboard_for_action(self, action: str) -> Dict:
        """Get appropriate keyboard for action."""
        action = self._normalize_action(action)
        if action == "menu":
            return self.keyboard()
        if action.startswith("menu:"):
            menu_type = action.split(":")[1]
            if menu_type == "copy_trading":
                return self.copy_trading_keyboard()
            elif menu_type == "mes_wallets":
                return self.mes_wallets_keyboard()
            elif menu_type == "decouvrir":
                return self.decouvrir_keyboard()
            elif menu_type == "parametres":
                return self.parametres_keyboard()
        if action in {"settings_menu", "settings_mode", "settings_mode_live", "settings_max_trade", "settings_slippage"}:
            return self.settings_keyboard()
        if action == "wallet_mirror":
            return self.wallet_selection_keyboard()
        if action == "user_wallet_select":
            return self.wallet_selection_keyboard()
        if action.startswith("select_wallet:"):
            return self.mes_wallets_keyboard()
        if action in {"mirror_add_prompt", "copy_pairs"}:
            return self.mirror_keyboard()
        if action in {"manual_trade", "manual_buy_prompt", "manual_sell_prompt", "check_balance"}:
            return self.manual_trade_keyboard()
        if action in {"trade_history", "active_trades"} or action.startswith("history"):
            return self.trades_keyboard()
        if action in {"history_next", "history_prev", "history_refresh"}:
            page = getattr(self, '_history_page', 0)
            return history_keyboard(page=page, total_pages=getattr(self, '_history_total_pages', 1))
        if action == "performance":
            return self.performance_keyboard()
        if action in {"wallet_search"}:
            return self.wallet_search_keyboard()
        if action in {"market_search"}:
            return self.market_search_keyboard()
        if action == "top_markets":
            return self.top_markets_keyboard()
        if action in {"market_themes", "trades_theme"} or action.startswith("theme_"):
            return self.paris_theme_keyboard()
        if action.startswith("whale_") or action == "whale_activity":
            return self.whale_activity_keyboard()
        if action == "smartcopy_ai_menu":
            return self.smartcopy_ai_menu_keyboard()
        if action in {"smartcopy_create", "smartcopy_mode_sim", "smartcopy_mode_live"}:
            return self.smartcopy_mode_keyboard()
        if action == "smart_copy_dashboard":
            return self.smartcopy_dashboard_keyboard()
        if action in {"risk_menu", "risk_settings", "slippage_settings", "risk_alerts"} or action.startswith("risk_wallet_"):
            return self.risk_keyboard()
        if action == "top_wallets_menu" or action.startswith("rank_") or action == "groq_analyze":
            return self.top_wallets_keyboard()
        
        # Default to main keyboard
        return self.keyboard()
    
    def home_text(self) -> str:
        """Generate home screen text."""
        from .ui.home import home_text
        return home_text()

    def _scan_wallet_result(self, wallet_address: str) -> str:
        """Scan a wallet address and return formatted analysis text with keyboard."""
        try:
            from services.wallet_scanner.analyzer import WalletAnalyzer
            from ..ui.messages import wallet_analysis_text
            
            # Basic wallet address validation
            if not wallet_address.startswith("0x") or len(wallet_address) != 42:
                short = f"{wallet_address[:6]}...{wallet_address[-3:]}" if len(wallet_address) >= 12 else wallet_address
                return f"⚠️ Adresse de wallet invalide : `{short}`"
            
            analyzer = WalletAnalyzer()
            scan_result = analyzer.scan_wallet(wallet_address)
            
            # If no trading data, try to enhance with leaderboard data
            if scan_result.get("stats", {}).get("total_trades", 0) == 0:
                scan_result = self._enhance_with_leaderboard(scan_result, wallet_address)
            
            text, keyboard = wallet_analysis_text(scan_result)
            return text, keyboard
        except Exception as e:
            logger.error("Failed to scan wallet %s: %s", wallet_address, e, exc_info=True)
            short = f"{wallet_address[:6]}...{wallet_address[-3:]}" if len(wallet_address) >= 12 else wallet_address
            return f"⚠️ Erreur lors de l'analyse du wallet `{short}`. Veuillez réessayer plus tard."
    
    def _enhance_with_leaderboard(self, scan_result: dict, wallet_address: str) -> dict:
        """Try to get data from leaderboard."""
        try:
            import requests
            from core.config import Config
            # Try to find wallet in leaderboard
            response = requests.get(
                f"{Config.GAMMA_API_HOST}/leaderboard",
                params={"limit": 1000},
                timeout=10
            )
            if response.ok:
                data = response.json()
                if isinstance(data, list):
                    for entry in data:
                        if entry.get("wallet", "").lower() == wallet_address.lower():
                            # Found wallet in leaderboard
                            stats = scan_result.get("stats", {})
                            stats["total_trades"] = int(entry.get("totalTrades", 0) or 0)
                            stats["win_rate"] = float(entry.get("winRate", 0) or 0)
                            stats["total_volume_usdc"] = float(entry.get("totalVolumeUsdc", 0) or 0)
                            stats["leaderboard_pnl"] = float(entry.get("pnl", 0) or 0)
                            scan_result["stats"] = stats
                            break
        except Exception as e:
            logger.warning("Could not enhance with leaderboard: %s", e)
        return scan_result

    def _handle_quick_copy(self, wallet_address: str) -> str:
        """Handle quick copy action for a wallet."""
        short = f"{wallet_address[:6]}...{wallet_address[-3:]}" if len(wallet_address) >= 12 else wallet_address
        return (
            f"🦞 *Quick Copy: {short}*\n\n"
            "Choisis le mode pour copier ce wallet :\n"
            "• 🧠 Smart Copy IA - analyse intelligente\n"
            "• 🪞 Mirror - copie directe des trades"
        )
    
    def _handle_wallet_orders(self, wallet_address: str) -> str:
        """Handle wallet orders display."""
        short = f"{wallet_address[:6]}...{wallet_address[-3:]}" if len(wallet_address) >= 12 else wallet_address
        try:
            from services.wallet_scanner.client import WalletScannerClient
            client = WalletScannerClient()
            orders = client.fetch_wallet_data("orders", {"maker": wallet_address, "limit": 10})
            
            if not orders:
                return (
                    f"📋 *Ordres du Wallet {short}*\n\n"
                    "⚠️ Aucun ordre trouvé pour ce wallet.\n"
                    "Cela peut arriver si le wallet n'a pas d'ordres ouverts."
                )
            
            lines = [f"📋 *Ordres du Wallet {short}*", ""]
            for order in orders[:10]:
                token = order.get("token_id", "")[:8] + "..."
                price = float(order.get("price", 0))
                size = float(order.get("size", 0))
                side = order.get("side", "BUY")
                lines.append(f"• {side}: {size} @ ${price:.3f} ({token})")
            
            return "\n".join(lines)
        except Exception as e:
            logger.warning("Failed to fetch orders: %s", e)
            return f"⚠️ Erreur lors de la récupération des ordres pour `{short}`."
    
    def _handle_wallet_positions(self, wallet_address: str) -> str:
        """Handle wallet positions display."""
        short = f"{wallet_address[:6]}...{wallet_address[-3:]}" if len(wallet_address) >= 12 else wallet_address
        try:
            from services.wallet_scanner.client import WalletScannerClient
            client = WalletScannerClient()
            # Try to get positions from CLOB API
            positions = client.fetch_wallet_data("positions", {"maker": wallet_address, "limit": 10})
            
            if not positions:
                return (
                    f"💼 *Positions du Wallet {short}*\n\n"
                    "⚠️ Aucune position trouvée pour ce wallet.\n"
                    "Le wallet est peut-être vide ou les données ne sont pas publiques."
                )
            
            lines = [f"💼 *Positions du Wallet {short}*", ""]
            for pos in positions[:10]:
                token = pos.get("token_id", "")[:8] + "..."
                size = float(pos.get("size", 0))
                avg_price = float(pos.get("average_price", 0))
                lines.append(f"• {size} @ ${avg_price:.3f} ({token})")
            
            return "\n".join(lines)
        except Exception as e:
            logger.warning("Failed to fetch positions: %s", e)
            return f"⚠️ Erreur lors de la récupération des positions pour `{short}`."
