from .base import *
from collections import defaultdict


class TelegramMarketMixin:
    def market_search_text(self) -> str:
        return (
            "*🔍 Market Search — Choose a filter*\n"
            "*Recherche de marché — Choisis un filtre*\n\n"
            'Choisis une catégorie ci-dessous ou écris un mot-clé personnalisé, ex: `/search bitcoin`, `/search trump`, `/search earnings`.'
        )

    def _market_filter_query(self, filter_name: str) -> tuple[str, str]:
        filters = {
            "politics": ("Politique", "politique élection"),
            "sports": ("Sport", "sport"),
            "crypto": ("Crypto", "bitcoin ethereum crypto"),
            "trump": ("Trump", "trump"),
            "finance": ("Finance", "finance earnings fed taux"),
            "geopolitics": ("Géopolitique", "géopolitique guerre"),
            "volume": ("Volume", "volume"),
            "trending": ("Tendances", "tendances"),
        }
        default_label = "Personnalisé"
        default_query = filter_name.replace("_", " ")
        return filters.get(filter_name, (default_label, default_query))

    def top_markets_text(self, limit: int = 10) -> str:
        trades = self._load_recent_market_trades(limit=1000)
        if not trades:
            return (
                "*🔥 Top marchés Polymarket*\n\n"
                "Aucune activité récente disponible pour classer les marchés.\n"
                "Réessaie plus tard ou utilise la recherche de marchés."
            )

        grouped = {}
        for trade in trades:
            key = (
                trade.get("market")
                or trade.get("conditionId")
                or trade.get("marketSlug")
                or trade.get("slug")
                or trade.get("title")
                or trade.get("question")
            )
            if not key:
                continue
            key = str(key)
            entry = grouped.setdefault(
                key,
                {
                    "count": 0,
                    "volume": 0.0,
                    "title": self._market_title(trade),
                    "slug": trade.get("slug") or trade.get("marketSlug") or trade.get("eventSlug"),
                },
            )
            entry["count"] += 1
            entry["volume"] += self._trade_amount(trade)
            if not entry.get("title"):
                entry["title"] = self._market_title(trade)
            if not entry.get("slug"):
                entry["slug"] = trade.get("slug") or trade.get("marketSlug") or trade.get("eventSlug")

        ranked = sorted(grouped.values(), key=lambda item: (item["count"], item["volume"]), reverse=True)[:limit]
        if not ranked:
            return "*🔥 Top marchés Polymarket*\n\nAucun marché exploitable trouvé dans l'activité récente."

        lines = [
            "*🔥 Top marchés Polymarket*",
            "",
            "Marchés classés par nombre de paris récents, puis volume observé.",
            "",
        ]
        for index, item in enumerate(ranked, 1):
            title = item.get("title") or "Marché sans titre"
            slug = item.get("slug")
            url = f"https://polymarket.com/event/{slug}" if slug else "https://polymarket.com/markets"
            lines.append(f"*#{index} {title}*")
            lines.append(f"Paris récents: `{item['count']}` | Volume observé: `${item['volume']:,.0f}`")
            lines.append(f"🔗 {url}")
            lines.append("")
        return "\n".join(lines)

    def _load_recent_market_trades(self, limit: int = 1000) -> List[Dict]:
        try:
            from services.polymarket_data_api import get_trades

            trades = get_trades(limit=limit)
            if trades:
                return trades
        except Exception as exc:
            logger.warning("Top markets Data API fallback triggered: %s", exc)

        local_file = Config.DATA_DIR / "whale_activity.jsonl"
        rows = []
        if not local_file.exists():
            return rows
        try:
            with local_file.open("r", encoding="utf-8") as file:
                for line in file:
                    if not line.strip():
                        continue
                    rows.append(json.loads(line))
        except Exception as exc:
            logger.warning("Unable to load local market activity: %s", exc)
        return rows[-limit:]

    @staticmethod
    def _trade_amount(trade: Dict) -> float:
        for key in ("amount", "size", "usdcSize", "volume"):
            try:
                value = float(trade.get(key, 0) or 0)
                if value:
                    return value
            except Exception:
                continue
        return 0.0

    @staticmethod
    def _market_title(trade: Dict) -> str:
        return (
            trade.get("marketTitle")
            or trade.get("title")
            or trade.get("question")
            or trade.get("market")
            or trade.get("slug")
            or ""
        )

    def _search_markets(self, query: str, label: Optional[str] = None) -> str:
        query = (query or "").strip()
        if not query:
            return self.market_search_text()

        title = label or query
        try:
            response = requests.get(
                f"{Config.GAMMA_API_HOST.rstrip('/')}/public-search",
                params={"q": query, "limit": 6},
                timeout=self.request_timeout,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.warning("Market search failed for %s: %s", query, e)
            return (
                f"*🔍 Market Search — {title}*\n"
                f"*Recherche de marché — {title}*\n\n"
                f"Recherche indisponible pour `{query}`.\n"
                "Réessaie plus tard ou utilise un mot-clé plus précis."
            )

        rows = self._extract_market_results(data)
        if not rows:
            return (
                f"*🔍 Market Search — {title}*\n"
                f"*Recherche de marché — {title}*\n\n"
                f"Aucun marché trouvé pour `{query}`.\n"
                "Essaie un autre filtre ou une recherche comme `/search bitcoin`."
            )

        lines = [f"*🔍 Market Search — {title}*", f"*Recherche de marché — {title}*", "", f"Résultats pour `{query}`:", ""]
        for i, item in enumerate(rows[:6], 1):
            name = item.get("title") or item.get("question") or item.get("name") or item.get("slug") or "Marché sans titre"
            slug = item.get("slug") or item.get("eventSlug")
            url = f"https://polymarket.com/event/{slug}" if slug else "https://polymarket.com/markets"
            volume = item.get("volume") or item.get("volumeNum") or item.get("liquidity") or item.get("liquidityNum")
            suffix = f" — vol./liq. : {volume}" if volume not in (None, "") else ""
            lines.append(f"{i}. [{name}]({url}){suffix}")
        return "\n".join(lines)

    @staticmethod
    def _extract_market_results(data) -> List[Dict]:
        if isinstance(data, list):
            candidates = data
        elif isinstance(data, dict):
            candidates = []
            for key in ("markets", "events", "results", "data"):
                value = data.get(key)
                if isinstance(value, list):
                    candidates.extend(value)
            if not candidates and any(k in data for k in ("title", "question", "slug")):
                candidates = [data]
        else:
            candidates = []
        return [item for item in candidates if isinstance(item, dict)]
