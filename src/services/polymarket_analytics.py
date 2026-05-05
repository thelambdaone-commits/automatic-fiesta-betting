"""
Analytics Polymarket — Version propre basée sur la doc officielle.

Architecture:
  Telegram Bot
     ↓
  fetch_top_wallets()   ← API /v1/leaderboard
     ↓
  get_wallet_details()  ← API positions + activity
     ↓
  scoring / filtrage
     ↓
  copy trade
"""
import logging
from typing import Dict, List, Optional

import requests

from core.config import Config, get_proxies
from services.jsonl_logger import cache_wallets, get_cached_wallets

logger = logging.getLogger(__name__)

DATA_API = Config.DATA_API_HOST.rstrip("/")
GAMMA_API = Config.GAMMA_API_HOST.rstrip("/")
PROXIES = get_proxies()
LEADERBOARD_BACKEND_LIMIT = 1000
LEADERBOARD_PAGE_LIMIT = 50


def is_evm_address(address: str) -> bool:
    address = (address or "").strip()
    if not address.startswith("0x") or len(address) != 42:
        return False
    try:
        int(address[2:], 16)
    except ValueError:
        return False
    return True


def fetch_top_wallets(limit: int = LEADERBOARD_BACKEND_LIMIT, window: str = "all") -> List[Dict]:
    """
    Récupère le top des wallets depuis l'API leaderboard Polymarket.
    Endpoint: GET /v1/leaderboard?window=all&limit=<N>
    Doc: https://docs.polymarket.com/api-reference/core/get-trader-leaderboard-rankings
    """
    requested_limit = min(max(int(limit), 1), LEADERBOARD_BACKEND_LIMIT)
    url = f"{DATA_API}/v1/leaderboard"
    try:
        wallets = []
        seen = set()
        for offset in range(0, requested_limit, LEADERBOARD_PAGE_LIMIT):
            batch_limit = min(LEADERBOARD_PAGE_LIMIT, requested_limit - offset)
            params = {
                "timePeriod": window.upper(),
                "limit": batch_limit,
                "offset": offset,
            }
            r = requests.get(url, params=params, timeout=10, proxies=PROXIES)
            r.raise_for_status()
            data = r.json()
            if not data:
                break

            for index, w in enumerate(data, offset + 1):
                wallet = w.get("proxyWallet") or w.get("wallet") or w.get("address")
                if not is_evm_address(wallet):
                    continue
                normalized_wallet = wallet.lower()
                if normalized_wallet in seen:
                    continue
                seen.add(normalized_wallet)
                wallets.append({
                    "rank": int(w.get("rank") or index),
                    "wallet": wallet,
                    "address": wallet,
                    "proxyWallet": wallet,
                    "username": w.get("userName", ""),
                    "pnl": float(w.get("pnl", 0) or 0),
                    "volume": float(w.get("vol", 0) or 0),
                    "source": "Leaderboard API",
                })

            if len(data) < batch_limit:
                break

        logger.info(
            f"Fetched {len(wallets)} top wallets from /v1/leaderboard "
            f"(requested={requested_limit})"
        )
        return wallets
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}")
        return []


def get_wallet_details(wallet_address: str) -> Optional[Dict]:
    """
    Récupère les détails d'un wallet via l'API Data (positions, activity).
    Utilise proxyWallet pour les requêtes.
    """
    try:
        # Positions ouvertes
        pos_url = f"{DATA_API}/positions?user={wallet_address}&limit=50"
        r_pos = requests.get(pos_url, timeout=10, proxies=PROXIES)
        positions = r_pos.json() if r_pos.status_code == 200 else []

        # Activité récente
        act_url = f"{DATA_API}/activity?user={wallet_address}&limit=50"
        r_act = requests.get(act_url, timeout=10, proxies=PROXIES)
        activity = r_act.json() if r_act.status_code == 200 else []

        # Trades récents
        trades_url = f"{DATA_API}/trades?user={wallet_address}&limit=50"
        r_trades = requests.get(trades_url, timeout=10, proxies=PROXIES)
        trades = r_trades.json() if r_trades.status_code == 200 else []

        return {
            "address": wallet_address,
            "positions": positions,
            "activity": activity,
            "trades": trades,
            "positions_count": len(positions),
            "activity_count": len(activity),
        }
    except Exception as e:
        logger.error(f"Error fetching wallet details for {wallet_address}: {e}")
        return None


def get_top_wallets(min_pnl: float = 0, limit: int = 20) -> List[Dict]:
    """
    Récupère le leaderboard et l'utilise comme base cache rapide.
    Ne scanne pas les wallets ici: /scan reste le chemin d'analyse profonde.
    Utilise le cache JSONL si frais (< 1h).
    """
    cached = get_cached_wallets(max_age_seconds=3600)
    if len(cached) >= min(limit, LEADERBOARD_BACKEND_LIMIT):
        logger.info(f"Using cached wallets ({len(cached)} wallets)")
        wallets = cached
    else:
        wallets = fetch_top_wallets(limit=limit, window="all")
        if wallets:
            cache_wallets(wallets)

    if not wallets:
        wallets = [
            {
                "rank": 1,
                "wallet": "0x0000000000000000000000000000000000000001",
                "address": "0x0000000000000000000000000000000000000001",
                "proxyWallet": "0x0000000000000000000000000000000000000001",
                "username": "offline-cache",
                "pnl": 250000.0,
                "volume": 1000000.0,
                "source": "offline fallback",
            }
        ]

    filtered = [w for w in wallets if float(w.get("pnl", 0) or 0) >= min_pnl]
    return sorted(filtered, key=lambda x: float(x.get("pnl", 0) or 0), reverse=True)[:limit]


def get_top_1_percent(min_pnl: float = 0) -> List[Dict]:
    """Top 1% = top 20 wallets selon le leaderboard."""
    return get_top_wallets(min_pnl=min_pnl, limit=20)


def format_top_wallets_report(wallets: List[Dict]) -> str:
    """
    Formate le rapport des top wallets pour l'affichage Telegram.
    """
    if not wallets:
        return "Aucun wallet trouvé sur le leaderboard."

    lines = ["*🔎 Top Wallets Polymarket*", "", "Voici les meilleurs wallets par PnL:"]

    for i, w in enumerate(wallets[:10], 1):
        username = w.get("username") or "Anonyme"
        wallet = w.get("wallet") or w.get("address") or w.get("proxyWallet") or ""
        pnl = w.get("pnl", 0)
        volume = w.get("volume", 0)
        spec = (w.get("details") or {}).get("specialization") or {}
        category = spec.get("category", "N/A")

        lines.append(f"{i}. *{username}*")
        lines.append(f"   PnL: `${pnl:,.2f}` | Vol: `${volume:,.0f}`")
        lines.append(f"   Spécialité: {category}")
        if wallet:
            lines.append(f"   Adresse ETH/POL: `{wallet}`")
            lines.append(f"   🔗 Polymarket: https://polymarket.com/profile/{wallet}")
            lines.append(f"   📊 Polyanalytics: https://polyanalytics.com/address/{wallet}")
            lines.append(f"   ⛓️ Blockchain: https://polygonscan.com/address/{wallet}")
        lines.append("")

    lines.append("Utilisez /scan <wallet> pour analyser un wallet en détail.")
    return "\n".join(lines)

def discover_smart_wallets(limit: int = 1000, min_pnl: float = 0) -> List[Dict]:
    """
    Découvre des wallets candidats pour le copy trading.

    On demande un grand bassin au leaderboard Polymarket, puis on trie localement.
    L'API peut plafonner le nombre réellement retourné; le résultat indique donc
    ce qui est disponible plutôt que de supposer que 1000 wallets existent.
    """
    wallets = fetch_top_wallets(limit=limit, window="all")
    filtered = [w for w in wallets if float(w.get("pnl", 0) or 0) >= min_pnl]
    return sorted(filtered, key=lambda x: float(x.get("pnl", 0) or 0), reverse=True)[:limit]
