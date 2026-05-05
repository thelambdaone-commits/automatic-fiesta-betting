from collections import Counter, defaultdict
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import time
from typing import Dict, List

import requests

logger = __import__('logging').getLogger(__name__)
BACKEND_LIMIT = 1000
PAGE_SIZE = 2
DEFAULT_DISPLAY_LIMIT = 10
MAX_DISPLAY_LIMIT = 250
THEME_RANK_LIMIT = 100
THEME_DETAIL_DISPLAY_LIMIT = 100
THEME_ALL_DISPLAY_LIMIT = 100
THEME_CACHE_MAX_AGE_SECONDS = 24 * 60 * 60
THEME_DETAIL_LIMIT = 20
THEME_REQUEST_TIMEOUT = 4
THEME_MAX_WORKERS = 12


@dataclass
class WalletScore:
    wallet: str
    total_pnl: float
    realized_pnl: float
    current_value: float
    win_rate: float
    total_trades: int
    rank: int = 0
    username: str = ""
    source: str = "API Polymarket"
    theme: str = "inconnu"


THEME_KEYWORDS = {
    "politique": ["election", "president", "senate", "congress", "trump", "biden", "poll", "politic"],
    "crypto": ["bitcoin", "btc", "ethereum", "eth", "solana", "sol", "crypto", "token", "fed"],
    "sport": ["nba", "nfl", "mlb", "soccer", "football", "tennis", "ufc", "championship"],
    "macro/news": ["inflation", "cpi", "rate", "gdp", "war", "ceasefire", "court", "tariff"],
    "culture/tech": ["movie", "oscar", "grammy", "ai", "openai", "apple", "tesla", "spacex"],
}

THEME_LABELS = {
    "politique": "🏛️ Politique",
    "crypto": "🌚 Crypto",
    "sport": "🥇 Sport",
    "macro/news": "🌍 Macro/news",
    "culture/tech": "🧠 Culture/tech",
    "diversifié": "🎲 Diversifié",
    "multi-marchés": "🧭 Multi-marchés",
    "inconnu": "❔ Inconnu",
}

WALLET_THEME_ORDER = [
    "politique",
    "crypto",
    "sport",
    "macro/news",
    "culture/tech",
    "diversifié",
    "multi-marchés",
]

THEME_SLUGS = {
    "politique": "politique",
    "crypto": "crypto",
    "sport": "sport",
    "macro/news": "macro_news",
    "culture/tech": "culture_tech",
    "diversifié": "diversifie",
    "multi-marchés": "multi_marches",
    "inconnu": "inconnu",
}

SLUG_THEMES = {slug: theme for theme, slug in THEME_SLUGS.items()}


THEME_TEXT_FIELDS = (
    "market",
    "title",
    "question",
    "eventTitle",
    "eventSlug",
    "slug",
    "description",
    "category",
)


class WalletRanker:
    def __init__(self, limit: int = 50):
        self.limit = limit
    
    def rank(self, limit: int = BACKEND_LIMIT) -> List[WalletScore]:
        """
        Charge le leaderboard via le cache JSONL alimenté par Polymarket.
        Aucun scan wallet ni autre API profonde ici: /top10 doit rester rapide.
        """
        try:
            from services.polymarket_analytics import get_top_wallets

            data = get_top_wallets(limit=min(max(limit, self.limit), BACKEND_LIMIT))
            scores = []
            for entry in data:
                wallet = entry.get("wallet") or entry.get("proxyWallet") or entry.get("address") or ""
                if not wallet:
                    continue

                if not (wallet.startswith("0x") and len(wallet) == 42):
                    continue

                pnl = float(entry.get("pnl", 0) or 0)
                if pnl <= 0:
                    continue

                score = WalletScore(
                    wallet=wallet,
                    total_pnl=pnl,
                    realized_pnl=pnl,
                    current_value=float(entry.get("volume", entry.get("vol", 0)) or 0),
                    win_rate=0.0,
                    total_trades=0,
                    rank=int(entry.get("rank") or 0),
                    username=entry.get("username") or entry.get("userName") or "",
                    source=entry.get("source", "Leaderboard API"),
                )
                scores.append(score)

            scores.sort(key=lambda x: x.total_pnl, reverse=True)
            return scores[:limit]

        except Exception as e:
            logger.error(f"Error fetching leaderboard: {e}")
            return []

    @staticmethod
    def infer_theme(rows: List[Dict]) -> str:
        text_parts = []
        explicit_categories = []
        for row in rows or []:
            for field in THEME_TEXT_FIELDS:
                value = row.get(field)
                if value:
                    text_parts.append(str(value).lower())
                    if field == "category":
                        explicit_categories.append(str(value).lower())

        joined = " ".join(text_parts)
        counts = Counter(
            {
                theme: sum(joined.count(keyword) for keyword in keywords)
                for theme, keywords in THEME_KEYWORDS.items()
            }
        )
        if counts and counts.most_common(1)[0][1] > 0:
            return counts.most_common(1)[0][0]

        for category in explicit_categories:
            for theme in THEME_KEYWORDS:
                if theme in category:
                    return theme

        unique_markets = len({part for part in text_parts if part})
        if unique_markets > 12:
            return "diversifié"
        if unique_markets > 3:
            return "multi-marchés"
        return "inconnu"

    def rank_by_theme(self, limit: int = DEFAULT_DISPLAY_LIMIT) -> List[WalletScore]:
        """
        Classe le Top N du leaderboard et enrichit chaque wallet avec un thème
        déduit des positions/activités publiques Polymarket.
        """
        scores = self.rank(limit=limit)
        if not scores:
            return []

        self.enrich_themes(scores)
        return scores

    def enrich_themes(self, scores: List[WalletScore]) -> List[WalletScore]:
        if not scores:
            return scores

        cache = self._load_theme_cache()
        now = time.time()
        missing = []
        for score in scores:
            key = score.wallet.lower()
            cached = cache.get(key) or {}
            cached_theme = cached.get("theme")
            if cached_theme and cached_theme != "inconnu" and now - float(cached.get("timestamp", 0) or 0) < THEME_CACHE_MAX_AGE_SECONDS:
                score.theme = cached["theme"]
            else:
                missing.append(score)

        if missing:
            fetched = self._fetch_themes_parallel(missing)
            for score in missing:
                theme = fetched.get(score.wallet.lower())
                if theme:
                    score.theme = theme
                    if theme != "inconnu":
                        cache[score.wallet.lower()] = {"theme": theme, "timestamp": now}
            self._save_theme_cache(cache)

        return scores

    def _fetch_themes_parallel(self, scores: List[WalletScore]) -> Dict[str, str]:
        themes = {}
        with ThreadPoolExecutor(max_workers=THEME_MAX_WORKERS) as executor:
            future_map = {executor.submit(self._fetch_wallet_theme, score.wallet): score.wallet for score in scores}
            for future in as_completed(future_map):
                wallet = future_map[future]
                try:
                    themes[wallet.lower()] = future.result()
                except Exception as exc:
                    logger.debug("Theme fetch failed for %s: %s", wallet, exc)
                    themes[wallet.lower()] = "inconnu"
        return themes

    def _fetch_wallet_theme(self, wallet: str) -> str:
        try:
            from services.polymarket_analytics import get_wallet_details

            details = get_wallet_details(wallet) or {}
            rows = []
            for key in ("positions", "activity", "trades"):
                value = details.get(key)
                if isinstance(value, list):
                    rows.extend(value)
            theme = self.infer_theme(rows)
            if theme != "inconnu":
                return theme
        except Exception as exc:
            logger.debug("Analytics theme fetch failed for %s: %s", wallet, exc)

        try:
            from core.config import Config, get_proxies
        except Exception as e:
            logger.debug("Unable to load config for theme fetch: %s", e)
            return "inconnu"

        data_api = Config.DATA_API_HOST.rstrip("/")
        proxies = get_proxies()
        rows = []
        for endpoint, params in (
            ("positions", {"user": wallet, "limit": THEME_DETAIL_LIMIT}),
            ("activity", {"user": wallet, "limit": THEME_DETAIL_LIMIT}),
            ("trades", {"user": wallet, "limit": THEME_DETAIL_LIMIT}),
        ):
            try:
                response = requests.get(
                    f"{data_api}/{endpoint}",
                    params=params,
                    timeout=THEME_REQUEST_TIMEOUT,
                    proxies=proxies,
                )
                if response.status_code == 200:
                    payload = response.json()
                    if isinstance(payload, list):
                        rows.extend(payload)
            except Exception as exc:
                logger.debug("Theme endpoint %s failed for %s: %s", endpoint, wallet, exc)
        return self.infer_theme(rows)

    @staticmethod
    def _theme_cache_file():
        from core.config import Config

        return Config.DATA_DIR / "wallet_theme_cache.json"

    def _load_theme_cache(self) -> Dict:
        try:
            cache_file = self._theme_cache_file()
            if cache_file.exists():
                with cache_file.open("r", encoding="utf-8") as file:
                    data = json.load(file)
                    return data if isinstance(data, dict) else {}
        except Exception as exc:
            logger.debug("Unable to load wallet theme cache: %s", exc)
        return {}

    def _save_theme_cache(self, cache: Dict):
        try:
            cache_file = self._theme_cache_file()
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with cache_file.open("w", encoding="utf-8") as file:
                json.dump(cache, file, indent=2)
        except Exception as exc:
            logger.debug("Unable to save wallet theme cache: %s", exc)

    @staticmethod
    def theme_slug(theme: str) -> str:
        return THEME_SLUGS.get(theme, str(theme or "inconnu").replace("/", "_").replace("-", "_"))

    @staticmethod
    def theme_from_slug(slug: str) -> str:
        return SLUG_THEMES.get(slug, slug.replace("_", "/"))

    @staticmethod
    def theme_label(theme: str) -> str:
        return THEME_LABELS.get(theme, theme)
    
    @staticmethod
    def short_wallet(wallet: str) -> str:
        if not wallet:
            return "N/A"
        return f"{wallet[:8]}...{wallet[-6:]}" if len(wallet) > 14 else wallet
    
    @staticmethod
    def polymarket_url(wallet: str) -> str:
        return f"https://polymarket.com/profile/{wallet}"

    @staticmethod
    def polyanalytics_url(wallet: str) -> str:
        return f"https://polyanalytics.com/address/{wallet}"

    @staticmethod
    def blockchain_url(wallet: str) -> str:
        return f"https://polygonscan.com/address/{wallet}"

    @staticmethod
    def to_prompt(scores: List[WalletScore]) -> str:
        rows = []
        for score in scores[:50]:
            rows.append(
                {
                    "rank": score.rank,
                    "wallet": score.wallet,
                    "username": score.username,
                    "pnl": round(score.total_pnl, 2),
                    "volume": round(score.current_value, 2),
                    "win_rate": round(score.win_rate, 4),
                    "trades": score.total_trades,
                    "source": score.source,
                }
            )
        return str(rows)

    @staticmethod
    def format_scores(
        scores: List[WalletScore],
        page: int = 0,
        display_limit: int = DEFAULT_DISPLAY_LIMIT,
        page_size: int = PAGE_SIZE,
    ) -> str:
        """
        Format leaderboard cache for Telegram. Affiche seulement le subset demandé,
        sans traiter ni scanner les 100 wallets.
        """
        if not scores:
            return "Aucun wallet trouvé sur le leaderboard."

        display_limit = min(max(display_limit, page_size), min(len(scores), MAX_DISPLAY_LIMIT))
        visible_scores = scores[:display_limit]
        total_pages = max(1, (len(visible_scores) - 1) // page_size + 1)
        page = min(max(page, 0), total_pages - 1)
        start = page * page_size
        end = min(start + page_size, len(visible_scores))

        lines = [f"*💯 Top {display_limit} Wallets Polymarket*", f"Page {page + 1}/{total_pages}", ""]
        lines.append("Temporalité: `all-time`")
        lines.append("Backend: `leaderboard cache`")
        lines.append("")

        for i, score in enumerate(visible_scores[start:end], start + 1):
            title = score.username or WalletRanker.short_wallet(score.wallet)
            rank = score.rank or i
            lines.append(f"*#{rank} {title}*")
            lines.append(f"PnL: `+{score.total_pnl:,.0f} USDC`")
            lines.append(f"Volume: `{score.current_value:,.0f} USDC`")
            lines.append(f"ETH/POL: `{score.wallet}`")
            lines.append(f"🔗 Polymarket: {WalletRanker.polymarket_url(score.wallet)}")
            lines.append(f"📊 Polyanalytics: {WalletRanker.polyanalytics_url(score.wallet)}")
            lines.append(f"⛓️ Blockchain: {WalletRanker.blockchain_url(score.wallet)}")
            lines.append("")

        lines.append("Pour l'analyse profonde: `/scan <wallet>`")
        return "\n".join(lines)

    @staticmethod
    def format_theme_scores(scores: List[WalletScore], display_limit: int = DEFAULT_DISPLAY_LIMIT) -> str:
        if not scores:
            return "Aucun wallet trouvé sur le leaderboard."

        display_limit = min(max(display_limit, 1), len(scores))
        groups = defaultdict(list)
        for score in scores[:display_limit]:
            groups[score.theme or "inconnu"].append(score)

        ordered_themes = sorted(
            groups.items(),
            key=lambda item: sum(score.total_pnl for score in item[1]),
            reverse=True,
        )

        lines = [f"*💯 Top {display_limit} Wallets Polymarket par thèmes*", ""]
        lines.append("Thèmes estimés via positions, activité et trades publics.")
        lines.append("")

        for theme, theme_scores in ordered_themes:
            total_pnl = sum(score.total_pnl for score in theme_scores)
            lines.append(f"*🎯 {theme}* - `{len(theme_scores)} wallet(s)` - `+{total_pnl:,.0f} USDC`")
            for score in sorted(theme_scores, key=lambda item: item.total_pnl, reverse=True):
                rank = score.rank or (scores.index(score) + 1)
                title = score.username or WalletRanker.short_wallet(score.wallet)
                lines.append(f"#{rank} {title} | PnL `+{score.total_pnl:,.0f} USDC`")
                lines.append(f"🔗 {WalletRanker.polymarket_url(score.wallet)}")
            lines.append("")

        lines.append("Pour l'analyse profonde: `/scan <wallet>`")
        return "\n".join(lines)

    @staticmethod
    def format_theme_menu(scores: List[WalletScore]) -> str:
        if not scores:
            return "Aucun wallet trouvé sur le leaderboard."

        groups = defaultdict(list)
        for score in scores:
            groups[score.theme or "inconnu"].append(score)

        lines = ["*🎯 Top wallets par thème*", ""]
        lines.append("Wallets classés par PnL, regroupés par thème estimé.")
        lines.append("Choisis un thème avec les boutons ci-dessous.")
        lines.append("Thèmes estimés depuis l'activité locale récente.")
        lines.append("")
        for theme in WALLET_THEME_ORDER:
            theme_scores = groups.get(theme, [])
            total_pnl = sum(score.total_pnl for score in theme_scores)
            lines.append(f"{WalletRanker.theme_label(theme)}: `{len(theme_scores)}` wallet(s), `+{total_pnl:,.0f} USDC`")
        unknown_count = len(groups.get("inconnu", []))
        if unknown_count:
            lines.append(f"Autres/non classés: `{unknown_count}` wallet(s)")
        return "\n".join(lines)

    @staticmethod
    def format_selected_theme_scores(
        scores: List[WalletScore],
        theme: str,
        display_limit: int = DEFAULT_DISPLAY_LIMIT,
    ) -> str:
        theme_scores = [score for score in scores if (score.theme or "inconnu") == theme]
        if not theme_scores:
            return f"Aucun wallet trouvé pour le thème {WalletRanker.theme_label(theme)}."

        display_limit = min(max(display_limit, 1), min(len(theme_scores), THEME_DETAIL_DISPLAY_LIMIT))
        theme_scores = sorted(theme_scores, key=lambda score: score.total_pnl, reverse=True)[:display_limit]
        lines = [f"*{WalletRanker.theme_label(theme)} - Top {display_limit} wallets Polymarket*", ""]
        lines.append("Thème estimé via positions, activité et trades publics.")
        lines.append("")
        for index, score in enumerate(theme_scores, 1):
            rank = score.rank or index
            title = score.username or WalletRanker.short_wallet(score.wallet)
            lines.append(f"*#{rank} {title}* - `+{score.total_pnl:,.0f} USDC`")
            lines.append(f"`{score.wallet}`")

        lines.append("Pour l'analyse profonde: `/scan <wallet>`")
        return "\n".join(lines)

    @staticmethod
    def format_top10_all_themes(
        scores: List[WalletScore],
        display_limit: int = THEME_ALL_DISPLAY_LIMIT,
    ) -> str:
        seen = set()
        unique = []
        for score in scores:
            if score.wallet not in seen:
                seen.add(score.wallet)
                unique.append(score)
        display_limit = min(max(display_limit, 1), min(len(unique), THEME_ALL_DISPLAY_LIMIT))
        sorted_scores = sorted(unique, key=lambda s: (s.total_pnl, s.current_value, s.win_rate), reverse=True)[:display_limit]
        lines = [f"*🏆 Top {display_limit} Wallets - All Thèmes*", ""]
        lines.append("👉 Clique sur un wallet pour voir plus de détails")
        lines.append("")
        for index, score in enumerate(sorted_scores, 1):
            rank = score.rank or index
            title = score.username or WalletRanker.short_wallet(score.wallet)
            theme_label = WalletRanker.theme_label(score.theme or "inconnu")
            # Badge performance
            if score.total_pnl > 100000:
                badge = " 🔥"
            elif score.total_pnl > 50000:
                badge = " 🚀"
            else:
                badge = ""
            lines.append(f"*#{rank} {title}*{badge} - {theme_label} - `+{score.total_pnl:,.0f} USDC`")
            lines.append(f"`{score.wallet}`")
        lines.append("📊 Source : multi-thèmes (top global)")
        lines.append("")
        lines.append("Pour l'analyse profonde: `/scan <wallet>`")
        return "\n".join(lines)

    @staticmethod
    def page_scores(
        scores: List[WalletScore],
        page: int = 0,
        display_limit: int = DEFAULT_DISPLAY_LIMIT,
        page_size: int = PAGE_SIZE,
    ) -> List[WalletScore]:
        if not scores:
            return []
        display_limit = min(max(display_limit, page_size), min(len(scores), MAX_DISPLAY_LIMIT))
        visible_scores = scores[:display_limit]
        total_pages = max(1, (len(visible_scores) - 1) // page_size + 1)
        page = min(max(page, 0), total_pages - 1)
        start = page * page_size
        end = min(start + page_size, len(visible_scores))
        return visible_scores[start:end]
