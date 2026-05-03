"""
Scan et analyse de wallets Polymarket.

Le scanner accepte les adresses EVM 0x: wallet Ethereum classique, proxy
Polymarket/Magic, ou Safe sur Polygon. Les historiques publics viennent de la
Data API Polymarket, pas d'un jeu de données statique.
"""
import logging
import math
from html import escape
from collections import Counter
from typing import Dict, List
from urllib.parse import quote, urlencode

import requests

from core.config import Config, get_proxies
from services.groq_advisor import GroqAdvisor
# Import local pour éviter les imports circulaires
# Utilise le nouveau nom de fonction

logger = logging.getLogger(__name__)


class WalletScanner:
    """Scanne un wallet Polymarket et l'analyse avec l'IA."""

    def __init__(self):
        self.data_api_host = Config.DATA_API_HOST.rstrip("/")
        self.gamma_api_host = Config.GAMMA_API_HOST.rstrip("/")
        self.groq = GroqAdvisor() if Config.GROQ_API_KEY else None

    def scan_wallet(self, address: str, leaderboard_pnl: float = None) -> Dict:
        result = {
            "address": self._normalize_address(address),
            "valid": False,
            "specialization": None,
            "recommendation": None,
            "stats": {},
            "positions": [],
            "closed_positions": [],
            "activity": [],
            "recent_trades": [],
            "error": None,
        }

        try:
            if not self._is_valid_address(result["address"]):
                result["error"] = "Adresse invalide"
                return result

            result["valid"] = True
            address = result["address"]
            profile = self._fetch_profile(address)
            profile_wallet = profile.get("proxyWallet") or address
            result["profile"] = profile
            result["profile_wallet"] = profile_wallet

            positions = self._fetch_data_api("positions", {"user": profile_wallet, "limit": 100})
            closed_positions = self._fetch_data_api("closed-positions", {"user": profile_wallet, "limit": 100})
            activity = self._fetch_data_api("activity", {"user": profile_wallet, "limit": 100})
            trades = self._fetch_data_api("trades", {"user": profile_wallet, "limit": 100, "takerOnly": "false"})
            value = self._fetch_data_api_value("value", {"user": profile_wallet})

            result["positions"] = positions
            result["closed_positions"] = closed_positions
            result["activity"] = activity
            result["value"] = value
            result["recent_trades"] = self._normalize_trades(trades or activity)

            # Utilise les données déjà récupérées au lieu d'importer get_wallet_details
            # Utilise le PnL du leaderboard s'il est fourni
            wallet_data = {
                "address": address,
                "positions": positions,
                "activity": activity,
                "trades": trades,
                "pnl": leaderboard_pnl,
            }
            result["pnl"] = wallet_data["pnl"]  # Ajoute le PnL au résultat
            result["stats"] = self._calculate_public_stats(
                positions=positions,
                closed_positions=closed_positions,
                activity=activity,
                trades=trades,
                value=value,
                wallet_data=wallet_data,
            )
            result["specialization"] = self._detect_specialization(
                trades=result["recent_trades"],
                positions=positions,
                closed_positions=closed_positions,
                wallet_data=wallet_data,
            )
            result["recommendation"] = (
                self._analyze_with_ia(result)
                if self.groq
                else self._basic_recommendation(result["stats"])
            )
            return result
        except Exception as e:
            logger.exception("Error scanning wallet")
            result["error"] = str(e)
            return result

    @staticmethod
    def _normalize_address(address: str) -> str:
        return (address or "").strip()

    def _is_valid_address(self, address: str) -> bool:
        address = self._normalize_address(address)
        if not address.startswith("0x") or len(address) != 42:
            return False
        try:
            int(address[2:], 16)
        except ValueError:
            return False
        return True

    def _fetch_data_api(self, endpoint: str, params: Dict) -> List[Dict]:
        url = f"{self.data_api_host}/{endpoint.lstrip('/')}"
        data = self._fetch_json(url, params)
        if data is None:
            return []

        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("data", "results", "items", endpoint.replace("-", "_")):
                value = data.get(key)
                if isinstance(value, list):
                    return value
        logger.debug("Unexpected Polymarket Data API payload for %s: %r", endpoint, data)
        return []

    def _fetch_data_api_value(self, endpoint: str, params: Dict) -> Dict:
        url = f"{self.data_api_host}/{endpoint.lstrip('/')}"
        data = self._fetch_json(url, params)
        return data if isinstance(data, dict) else {}

    def _fetch_profile(self, address: str) -> Dict:
        url = f"{self.gamma_api_host}/public-profile"
        data = self._fetch_json(url, {"address": address}, warn=False)
        return data if isinstance(data, dict) else {}

    def _fetch_json(self, url: str, params: Dict, warn: bool = True):
        try:
            response = requests.get(
                url,
                params=params,
                proxies=get_proxies(),
                timeout=Config.REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if warn:
                logger.warning("Polymarket API failed for %s?%s: %s", url, urlencode(params), e)
            return None

    @staticmethod
    def _to_float(value, default: float = 0.0) -> float:
        try:
            if value is None or value == "":
                return default
            number = float(value)
            return number if math.isfinite(number) else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _first(item: Dict, keys: List[str], default=None):
        for key in keys:
            value = item.get(key)
            if value not in (None, ""):
                return value
        return default

    def _normalize_trades(self, rows: List[Dict]) -> List[Dict]:
        normalized = []
        for row in rows[:100]:
            cash = self._cash_value(row)
            normalized.append(
                {
                    "timestamp": self._first(row, ["timestamp", "timeStamp", "createdAt", "created_at", "updatedAt"]),
                    "market": self._first(row, ["title", "marketTitle", "market_title", "question", "eventTitle", "event_slug", "slug"], "unknown"),
                    "outcome": self._first(row, ["outcome", "outcomeName", "asset", "tokenId", "tokenID"], "unknown"),
                    "side": str(self._first(row, ["side", "type", "action"], "unknown")).upper(),
                    "size": self._to_float(self._first(row, ["size", "amount", "shares", "makerAmount", "takerAmount"])),
                    "price": self._to_float(self._first(row, ["price", "avgPrice", "averagePrice"])),
                    "cash": cash,
                    "tx_hash": self._first(row, ["transactionHash", "transaction_hash", "txHash", "hash"], ""),
                }
            )
        return normalized

    def _cash_value(self, row: Dict) -> float:
        cash = self._to_float(self._first(row, ["cash", "value", "usdcSize", "notional", "volume"]))
        if cash:
            return cash
        size = self._to_float(self._first(row, ["size", "amount", "shares", "makerAmount", "takerAmount"]))
        price = self._to_float(self._first(row, ["price", "avgPrice", "averagePrice"]))
        return round(size * price, 6) if size and price else 0.0

    def _market_url(self, row: Dict) -> str:
        slug = self._first(row, ["slug", "marketSlug", "market_slug", "eventSlug", "event_slug"])
        if slug:
            return f"https://polymarket.com/event/{slug}"
        title = self._first(row, ["title", "marketTitle", "market_title", "question", "eventTitle", "market"])
        if title:
            return f"https://polymarket.com/search?query={quote(str(title))}"
        condition_id = self._first(row, ["conditionId", "condition_id", "marketId", "market_id"])
        if condition_id:
            return f"https://polymarket.com/search?query={quote(str(condition_id))}"
        return ""

    def _format_open_positions_html(self, positions: List[Dict], limit: int = 5) -> List[str]:
        if not positions:
            return ["  - Aucune position ouverte publique"]

        lines = []
        for index, position in enumerate(positions[:limit], 1):
            title = self._first(position, ["title", "marketTitle", "market_title", "question", "eventTitle"], "Marche inconnu")
            outcome = self._first(position, ["outcome", "outcomeName", "asset", "tokenId", "tokenID"], "N/A")
            value = self._to_float(self._first(position, ["currentValue", "current_value", "value", "cashValue"]))
            size = self._to_float(self._first(position, ["size", "amount", "shares"]))
            pnl = self._to_float(self._first(position, ["cashPnl", "realizedPnl", "unrealizedPnl", "pnl"]))
            url = self._market_url(position)

            title_text = escape(str(title)[:90])
            if url:
                lines.append(f'  {index}. <a href="{escape(url)}">{title_text}</a>')
            else:
                lines.append(f"  {index}. {title_text}")
            lines.append(f"     Outcome: <code>{escape(str(outcome))}</code>")
            if value:
                lines.append(f"     Valeur: <code>{value:,.2f} USDC</code>")
            if size:
                lines.append(f"     Size: <code>{size:,.4f}</code>")
            if pnl:
                lines.append(f"     PnL: <code>{pnl:+,.2f} USDC</code>")

        remaining = len(positions) - limit
        if remaining > 0:
            lines.append(f"  - +{remaining} autres positions ouvertes")
        return lines

    def _wallet_state_html(self, result: Dict) -> List[str]:
        stats = result.get("stats", {})
        positions = result.get("positions", [])
        value = result.get("value") or {}
        portfolio_value = float(stats.get("portfolio_value", 0) or 0)
        public_value = self._to_float(
            self._first(value, ["cash", "balance", "value", "totalValue", "portfolioValue", "currentValue", "cashValue"])
        )
        open_count = int(stats.get("open_positions", 0) or len(positions or []))
        has_positions = open_count > 0
        has_public_value = max(portfolio_value, public_value) > 0

        if has_positions and has_public_value:
            status = "✅ Fonds/valeur publique et positions actives détectés"
        elif has_positions:
            status = "✅ Positions actives détectées, fonds publics non confirmés"
        elif has_public_value:
            status = "⚠️ Valeur publique détectée, aucune position ouverte récupérée"
        else:
            status = "⚠️ Aucun fonds public ni position ouverte détecté via l'API"

        return [
            f"  - Statut: <b>{status}</b>",
            f"  - Positions actives: <code>{open_count}</code>",
            f"  - Valeur publique détectée: <code>{max(portfolio_value, public_value):,.2f} USDC</code>",
            "  - Note: la Data API publique peut masquer le cash exact; la valeur affichée est la meilleure estimation publique.",
        ]

    def _calculate_public_stats(
        self,
        positions: List[Dict],
        closed_positions: List[Dict],
        activity: List[Dict],
        trades: List[Dict],
        value: Dict,
        wallet_data: Dict | None,
    ) -> Dict:
        trade_rows = trades or [
            row for row in activity if str(row.get("type", "")).lower() in {"trade", "buy", "sell"}
        ]
        closed_pnls = [
            self._to_float(self._first(row, ["realizedPnl", "realized_pnl", "pnl", "cashPnl", "percentPnl"]))
            for row in closed_positions
        ]
        closed_pnls = [pnl for pnl in closed_pnls if pnl != 0]
        volume = sum(self._cash_value(row) for row in trade_rows)
        current_value = sum(
            self._to_float(self._first(row, ["currentValue", "current_value", "value", "cashValue"]))
            for row in positions
        )
        current_value = current_value or self._to_float(
            self._first(value, ["value", "totalValue", "portfolioValue", "currentValue", "cashValue"])
        )
        realized_pnl = sum(closed_pnls)
        win_rate = (sum(1 for pnl in closed_pnls if pnl > 0) / len(closed_pnls)) if closed_pnls else 0.0

        if wallet_data:
            volume = volume or self._to_float(wallet_data.get("volume"))
            current_value = current_value or self._to_float(wallet_data.get("portfolio_value"))
            realized_pnl = realized_pnl or self._to_float(wallet_data.get("profit") or wallet_data.get("pnl"))
            win_rate = win_rate or self._to_float(wallet_data.get("win_rate"))

        markets = {
            str(self._first(row, ["conditionId", "condition_id", "market", "marketId", "slug", "title", "question"], ""))
            for row in trade_rows + positions + closed_positions
        }
        markets.discard("")

        return {
            "total_trades": len(trade_rows) or (wallet_data or {}).get("trades", 0),
            "total_volume_usdc": round(volume, 2),
            "portfolio_value": round(current_value, 2),
            "profit": round(realized_pnl, 2),
            "win_rate": round(win_rate, 4),
            "unique_markets": len(markets),
            "open_positions": len(positions),
            "closed_positions": len(closed_positions),
        }

    def _detect_specialization(
        self,
        trades: List[Dict],
        positions: List[Dict] | None = None,
        closed_positions: List[Dict] | None = None,
        wallet_data: Dict | None = None,
    ) -> Dict:
        if wallet_data and wallet_data.get("specialization"):
            return {"category": wallet_data["specialization"], "confidence": 0.8, "details": "Wallet connu localement"}

        text_rows = trades + self._normalize_trades((positions or []) + (closed_positions or []))
        joined = " ".join(str(row.get("market", "")).lower() for row in text_rows)
        categories = {
            "politique": ["election", "president", "senate", "congress", "trump", "biden", "poll", "politic"],
            "crypto": ["bitcoin", "btc", "ethereum", "eth", "solana", "sol", "crypto", "token", "fed"],
            "sport": ["nba", "nfl", "mlb", "soccer", "football", "tennis", "ufc", "championship"],
            "macro/news": ["inflation", "cpi", "rate", "gdp", "war", "ceasefire", "court"],
            "culture/tech": ["movie", "oscar", "grammy", "ai", "openai", "apple", "tesla", "spacex"],
        }
        counts = Counter(
            {
                category: sum(joined.count(keyword) for keyword in keywords)
                for category, keywords in categories.items()
            }
        )

        if counts and counts.most_common(1)[0][1] > 0:
            category, hits = counts.most_common(1)[0]
            confidence = min(0.9, 0.45 + hits / max(10, len(text_rows) or 1))
            return {"category": category, "confidence": round(confidence, 2), "details": f"{hits} signaux dans l'historique"}

        unique_markets = len({row.get("market") for row in text_rows if row.get("market")})
        if unique_markets > 20:
            return {"category": "diversifié", "confidence": 0.65, "details": "Beaucoup de marchés différents"}
        if unique_markets > 5:
            return {"category": "multi-marchés", "confidence": 0.55, "details": "Plusieurs marchés sans catégorie dominante"}
        return {"category": "unknown", "confidence": 0.0, "details": "Historique public insuffisant"}

    def _analyze_with_ia(self, wallet_data: Dict) -> str:
        try:
            stats = wallet_data.get("stats", {})
            spec = wallet_data.get("specialization", {})
            recent = wallet_data.get("recent_trades", [])[:15]
            positions = wallet_data.get("positions", [])[:10]
            closed_positions = wallet_data.get("closed_positions", [])[:15]

            prompt = f"""
Analyze this Polymarket wallet and provide:
1. What is this wallet specialized in? (politics, sports, crypto, general/news, etc.)
2. Is this wallet good for Wallet Mirror copy trading? (yes/no)
3. Risk level: (low/medium/high)
4. Recommended mirror size: (percentage of their trades)
5. Summarize the old bets: what the wallet historically bought/sold, themes, PnL quality, and data limitations.

Wallet data:
- Address: {wallet_data['address']}
- Profile wallet: {wallet_data.get('profile_wallet', wallet_data['address'])}
- Total trades: {stats.get('total_trades', 0)}
- Total volume: {stats.get('total_volume_usdc', 0)} USDC
- Portfolio value: {stats.get('portfolio_value', 0)} USDC
- Profit/PnL: {stats.get('profit', 0)} USDC
- Win Rate: {stats.get('win_rate', 0)}
- Unique markets: {stats.get('unique_markets', 0)}
- Open positions: {stats.get('open_positions', 0)}
- Closed positions: {stats.get('closed_positions', 0)}
- Detected specialization: {spec.get('category', 'unknown')}
- Recent trades/activity: {recent[:10]}
- Open positions sample: {positions[:5]}
- Closed positions sample: {closed_positions[:8]}

Provide a concise analysis in French since the user speaks French.
Return Telegram-ready text, short and readable. Do not invent missing stats.
If data is insufficient, say exactly what is missing.
Use format:
SPECIALISATION: [category]
WALLET MIRROR: [oui/non]
RISQUE: [low/medium/high]
TAILLE MIROIR: [%]
ANCIENS PARIS: [resume precis de l'historique fourni]
ANALYSE: [2-3 phrases]
"""
            response = self.groq.complete(
                user=prompt,
                system=(
                    "You are a risk-aware Polymarket wallet analyst. Use only the provided data, "
                    "state uncertainty, and never guarantee profit."
                ),
                timeout=45,
                max_tokens=700,
            )
            return response.strip()
        except Exception as e:
            logger.error("IA analysis failed: %s", e)
            return self._basic_recommendation(wallet_data.get("stats", {}))

    def _basic_recommendation(self, stats: Dict) -> str:
        if not stats:
            return "Donnees insuffisantes"

        trades = stats.get("total_trades", 0)
        volume = stats.get("total_volume_usdc", 0)
        win_rate = stats.get("win_rate", 0)

        if trades < 10:
            return f"Peu de trades ({trades}). Attendre plus d'historique avant Wallet Mirror."
        if volume < 100:
            return f"Volume faible ({volume} USDC). Risque eleve pour Wallet Mirror."
        if win_rate and win_rate < 0.45:
            return f"Win rate faible ({win_rate:.1%}). Wallet Mirror deconseille sans filtre manuel."
        return f"Wallet actif avec {trades} trades et {volume} USDC de volume. Wallet Mirror possible avec sizing conservateur."

    @staticmethod
    def polymarket_profile_url(address: str) -> str:
        return f"https://polymarket.com/profile/{address}"

    @staticmethod
    def polymarket_analytics_url(address: str) -> str:
        return f"https://polyanalytics.com/address/{address}"

    @staticmethod
    def blockchain_url(address: str) -> str:
        return f"https://polygonscan.com/address/{address}"

    def format_report(self, result: Dict) -> str:
        if not result.get("valid"):
            return f"Erreur: {result.get('error', 'Erreur inconnue')}"

        address = result["address"]
        profile_wallet = result.get("profile_wallet", address)
        short = f"{address[:6]}...{address[-4:]}"
        stats = result.get("stats", {})
        spec = result.get("specialization", {})
        recommendation = result.get("recommendation") or "Non disponible"
        pnl = result.get("pnl", 0)  # Utilise le PnL du leaderboard si disponible
        win_rate = stats.get("win_rate", 0)
        pnl_text = "N/A" if pnl is None else f"{float(pnl or 0):+,.2f} USDC"
        recommendation_html = escape(str(recommendation))

        lines = [
            f"<b>Scan Wallet Mirror {escape(short)}</b>",
            "",
            "<b>Liens</b>",
            f'  - <a href="{escape(self.polymarket_profile_url(address))}">Polymarket</a>',
            f'  - <a href="{escape(self.polymarket_analytics_url(profile_wallet))}">Polyanalytics</a>',
            f'  - <a href="{escape(self.blockchain_url(profile_wallet))}">Blockchain</a>',
            "",
            "<b>Adresses copiables</b>",
            f"  - ETH/POL: <code>{escape(address)}</code>",
            f"  - Proxy Polymarket/Polygon: <code>{escape(profile_wallet)}</code>",
            "",
            "<b>Statistiques publiques</b>",
            f"  - Trades récupérés: <code>{int(stats.get('total_trades', 0) or 0):,}</code>",
            f"  - Volume récupéré: <code>{float(stats.get('total_volume_usdc', 0) or 0):,.2f} USDC</code>",
            f"  - PnL leaderboard: <code>{escape(pnl_text)}</code>",
            f"  - PnL/profit fermé: <code>{float(stats.get('profit', 0) or 0):+,.2f} USDC</code>",
            f"  - Valeur positions ouvertes: <code>{float(stats.get('portfolio_value', 0) or 0):,.2f} USDC</code>",
            f"  - Win rate estimé: <code>{float(win_rate or 0):.1%}</code>",
            f"  - Marchés uniques récupérés: <code>{int(stats.get('unique_markets', 0) or 0)}</code>",
            f"  - Positions ouvertes/fermees: {stats.get('open_positions', 0)}/{stats.get('closed_positions', 0)}",
            "  - Source: Data API publique Polymarket, limites API appliquées",
            "",
            "<b>État wallet</b>",
            *self._wallet_state_html(result),
            "",
            "<b>Positions ouvertes cliquables</b>",
            *self._format_open_positions_html(result.get("positions", [])),
            "",
            "<b>Spécialisation</b>",
            f"  - Categorie: {spec.get('category', 'inconnue')}",
            f"  - Confiance: {int(spec.get('confidence', 0) * 100)}%",
            f"  - Detail: {escape(str(spec.get('details', 'n/a')))}",
            "",
            "<b>Analyse IA / Wallet Mirror</b>",
            recommendation_html,
        ]
        return "\n".join(str(line) for line in lines)


def scan_and_report(address: str) -> str:
    scanner = WalletScanner()
    result = scanner.scan_wallet(address)
    return scanner.format_report(result)
