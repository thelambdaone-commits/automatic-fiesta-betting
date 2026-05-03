from .base import *


class TelegramTopWalletsMixin:
    def _handle_top10_all_themes(self) -> str:
        if not self._rank_scores:
            self._rank_scores = WalletRanker().rank(limit=THEME_RANK_LIMIT)
        if not self._rank_scores:
            return "Aucun wallet trouvé dans le classement. Vérifiez l'API Polymarket."
        return WalletRanker.format_top10_all_themes(self._rank_scores, display_limit=THEME_ALL_DISPLAY_LIMIT)

    def _handle_groq_wallet(self, wallet: str) -> str:
        import time
        now = time.time()
        last_call = getattr(self, "_last_wallet_call", {})
        if wallet in last_call and now - last_call[wallet] < 10:
            return "⏳ Attends quelques secondes avant de réanalyser ce wallet..."
        last_call[wallet] = now
        self._last_wallet_call = last_call
        try:
            from services.groq_advisor import GroqAdvisor
            scores = [s for s in getattr(self, "_rank_scores", []) if s.wallet == wallet]
            return GroqAdvisor().analyze_wallets(scores[:1])
        except Exception as e:
            logger.warning("Groq wallet analysis failed: %s", e)
            return f"Analyse IA indisponible : {e}"

    def _handle_trades_wallet(self, wallet: str) -> str:
        import time
        now = time.time()
        last_call = getattr(self, "_last_wallet_call", {})
        if wallet in last_call and now - last_call[wallet] < 10:
            return "⏳ Attends quelques secondes avant de refaire cette action..."
        last_call[wallet] = now
        self._last_wallet_call = last_call
        try:
            from services.whale_activity import WhaleActivity
            activity = WhaleActivity()
            return activity.format_wallet_activity(wallet)
        except Exception as e:
            logger.warning("Trades fetch failed: %s", e)
            return f"Historique des trades indisponible : {e}"

    def _handle_mirror_add(self, wallet: str) -> str:
        try:
            self._save_wallet_mirror_target(wallet)
            return f"✅ Wallet {WalletRanker.short_wallet(wallet)} ajouté au copy trading."
        except Exception as e:
            logger.warning("Mirror add failed: %s", e)
            return f"Erreur ajout wallet: {e}"

    def _top_wallets_menu(self) -> str:
        """Menu top wallets avec options"""
        lines = [
            "*💯 Meilleurs wallets Polymarket*",
            "",
            "Classement des wallets par PnL leaderboard.",
            "",
            "Choisis une option:",
            "• Top 10 / Top 20 / Top 50 - wallets avec le plus de PnL",
            "• /scan <wallet> - analyser un wallet précis",
            "",
            "Pour les marchés les plus actifs, utilise Découvrir → Top marchés."
        ]
        return "\n".join(lines)
    @staticmethod
    def top_wallets_keyboard() -> Dict:
        return {
            "inline_keyboard": [
                [
                    {"text": "⬅️", "callback_data": "rank_prev"},
                    {"text": "➡️", "callback_data": "rank_next"},
                    {"text": "❌", "callback_data": "rank_close"},
                ],
                [
                    {"text": "Top 10", "callback_data": "rank_wallets"},
                    {"text": "Top 20", "callback_data": "rank_wallets_20"},
                    {"text": "Top 50", "callback_data": "rank_wallets_50"},
                ],
                [
                    {"text": "🎯 Wallets par thème", "callback_data": "rank_wallets_themes"},
                ],
                [
                    {"text": "🧠 IA wallets", "callback_data": "groq_analyze"},
                    {"text": "⬅️ Découvrir", "callback_data": "menu:decouvrir"},
                ],
                [
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        }

    def top_wallets_page_keyboard(self) -> Dict:
        rows = [
            [
                {"text": "⬅️", "callback_data": "rank_prev"},
                {"text": "➡️", "callback_data": "rank_next"},
                {"text": "❌", "callback_data": "rank_close"},
            ]
        ]

        page_scores = WalletRanker.page_scores(
            self._rank_scores,
            self._rank_page,
            getattr(self, "_rank_display_limit", 10),
        )
        for score in page_scores:
            rank = score.rank or (self._rank_scores.index(score) + 1)
            short = WalletRanker.short_wallet(score.wallet)
            rows.append([
                {"text": f"🔍 Scan #{rank} {short}", "callback_data": f"scan_{score.wallet}"},
                {"text": "🦞 Copier", "callback_data": f"quick_copy_{score.wallet}"},
            ])

        rows.extend(
            [
                [
                    {"text": "Top 10", "callback_data": "rank_wallets"},
                    {"text": "Top 20", "callback_data": "rank_wallets_20"},
                    {"text": "Top 50", "callback_data": "rank_wallets_50"},
                ],
                [
                    {"text": "🎯 Wallets par thème", "callback_data": "rank_wallets_themes"},
                ],
                [
                    {"text": "🧠 IA wallets", "callback_data": "groq_analyze"},
                    {"text": "⬅️ Découvrir", "callback_data": "menu:decouvrir"},
                ],
                [
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        )
        return {"inline_keyboard": rows}

    def top_wallets_themes_keyboard(self) -> Dict:
        from services.wallet_ranker import WALLET_THEME_ORDER

        themes = list(WALLET_THEME_ORDER)

        rows = []
        for index in range(0, len(themes), 2):
            row = []
            for theme in themes[index:index + 2]:
                row.append({
                    "text": WalletRanker.theme_label(theme),
                    "callback_data": f"rank_theme_{WalletRanker.theme_slug(theme)}",
                })
            rows.append(row)

        rows.append([
            {"text": "🏆 Top 50 all thèmes", "callback_data": "rank_theme_top10_all"},
        ])

        rows.extend(
            [
                [
                    {"text": "🔄 Actualiser thèmes", "callback_data": "rank_wallets_themes"},
                    {"text": "⬅️ Meilleurs wallets", "callback_data": "rank_wallets"},
                ],
                [
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        )
        return {"inline_keyboard": rows}

    def top_wallets_theme_detail_keyboard(self) -> Dict:
        selected_theme = getattr(self, "_rank_selected_theme", "")
        rows = []
        for score in getattr(self, "_rank_scores", []):
            if (getattr(score, "theme", "") or "inconnu") != selected_theme:
                continue
            rank = score.rank or (self._rank_scores.index(score) + 1)
            short = WalletRanker.short_wallet(score.wallet)
            rows.append([{"text": f"🔍 #{rank} {short}", "callback_data": f"scan_{score.wallet}"}])
            if len(rows) >= 20:
                break

        rows.extend(
            [
                [
                    {"text": "⬅️ Thèmes", "callback_data": "rank_wallets_themes"},
                    {"text": "🔄 Actualiser", "callback_data": f"rank_theme_{WalletRanker.theme_slug(selected_theme)}"},
                ],
                [
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        )
        return {"inline_keyboard": rows}

    def top_wallets_top10_all_keyboard(self) -> Dict:
        scores = getattr(self, "_rank_scores", [])
        seen_wallets = set()
        unique_scores = []
        for score in scores:
            if score.wallet not in seen_wallets:
                seen_wallets.add(score.wallet)
                unique_scores.append(score)
        sorted_scores = sorted(unique_scores, key=lambda s: (s.total_pnl, s.current_value, s.win_rate), reverse=True)[:20]
        rows = []
        for score in sorted_scores:
            rank = score.rank or (scores.index(score) + 1) if score in scores else 0
            short = WalletRanker.short_wallet(score.wallet)
            rows.append([{"text": f"🔍 #{rank} {short}", "callback_data": f"scan_{score.wallet}"}])
            rows.append([
                {"text": "🧠 IA", "callback_data": f"groq_{score.wallet}"},
                {"text": "📡 Trades", "callback_data": f"trades_{score.wallet}"},
                {"text": "🪞 Copier", "callback_data": f"mirror_add_{score.wallet}"},
            ])
        rows.extend(
            [
                [
                    {"text": "⬅️ Thèmes", "callback_data": "rank_wallets_themes"},
                    {"text": "🔄 Actualiser", "callback_data": "rank_theme_top10_all"},
                ],
                [
                    {"text": "🏠 Accueil", "callback_data": "menu"},
                ],
            ]
        )
        return {"inline_keyboard": rows}
