"""
Whale Activity Monitor for Polymarket.

Fetches recent trades from top wallets (whales) using the `/activity` API.
Runs polling every 5 minutes, caches results in `data/whale_activity.jsonl`.
"""
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.parse import quote

import requests

from core.config import Config, get_proxies
from services.polymarket_analytics import fetch_top_wallets
from services.jsonl_logger import append_record, read_records, _jsonl_path

logger = logging.getLogger(__name__)
DATA_API = Config.DATA_API_HOST.rstrip("/")
PROXIES = get_proxies()

POLLING_INTERVAL = 300  # 5 minutes


def fetch_wallet_activity(wallet_address: str, limit: int = 5) -> List[Dict]:
    """
    Fetch recent activity for a given wallet using the /activity endpoint.
    """
    url = f"{DATA_API}/activity"
    params = {"user": wallet_address, "limit": limit}
    try:
        r = requests.get(url, params=params, timeout=10, proxies=PROXIES)
        r.raise_for_status()
        data = r.json()
        # Filter for actual trades (buy/sell)
        trades = [
            t for t in data
            if str(t.get("type", "")).lower() in {"trade", "buy", "sell"}
            or str(t.get("side", "")).upper() in {"BUY", "SELL"}
        ]
        for t in trades:
            t["wallet"] = wallet_address
        return trades[:limit]
    except Exception as e:
        logger.warning(f"Failed to fetch activity for {wallet_address}: {e}")
        return []


def get_recent_whale_trades(top_n: int = 10, activity_limit: int = 5) -> List[Dict]:
    """
    Aggregate recent trades from the top N whales.
    Uses cache if fresh (< POLLING_INTERVAL old).
    """
    # Check cache first
    cached = read_records("whale_activity", limit=top_n * activity_limit)
    if cached:
        newest_ts = max(r.get("_ts", 0) for r in cached)
        if time.time() - newest_ts < POLLING_INTERVAL:
            logger.info(f"Using cached whale activity ({len(cached)} trades)")
            return cached

    # Fetch fresh data
    whales = fetch_top_wallets(limit=top_n, window="all")
    all_trades = []
    seen = set()

    for w in whales:
        wallet = w.get("wallet") or w.get("proxyWallet")
        if not wallet:
            continue
        trades = fetch_wallet_activity(wallet, limit=activity_limit)
        for t in trades:
            # Deduplicate by a simple key
            key = ":".join(
                str(part or "")
                for part in [
                    wallet,
                    t.get("transactionHash") or t.get("transaction_hash") or t.get("txHash") or t.get("hash"),
                    t.get("timestamp") or t.get("createdAt"),
                    t.get("tokenId") or t.get("asset") or t.get("outcome"),
                    t.get("side") or t.get("type"),
                ]
            )
            if key not in seen:
                seen.add(key)
                all_trades.append(t)

    # Sort by timestamp descending (most recent first)
    all_trades.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

    # Cache to JSONL
    path = _jsonl_path("whale_activity")
    with open(path, mode="w", encoding="utf-8") as f:
        for t in all_trades:
            record = {
                "wallet": t.get("wallet", ""),
                "type": t.get("type", ""),
                "side": t.get("side", ""),
                "tokenId": _first(t, ["tokenId", "tokenID", "asset", "outcome", "outcomeName"], ""),
                "market": _first(t, ["title", "marketTitle", "market_title", "question", "eventTitle", "slug"], ""),
                "slug": _first(t, ["slug", "marketSlug", "market_slug", "eventSlug", "event_slug"], ""),
                "amount": _trade_amount(t),
                "timestamp": _timestamp(t),
                "_ts": time.time(),
                "_iso": datetime.now(timezone.utc).isoformat(),
            }
            line = json.dumps(record, ensure_ascii=False)
            f.write(line + "\n")

    return all_trades


def _first(item: Dict, keys: List[str], default=None):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return default


def _to_float(value, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _trade_amount(trade: Dict) -> float:
    direct = _to_float(_first(trade, ["amount", "cash", "value", "usdcSize", "notional", "volume", "sizeUsd"]))
    if direct:
        return direct
    size = _to_float(_first(trade, ["size", "shares", "makerAmount", "takerAmount"]))
    price = _to_float(_first(trade, ["price", "avgPrice", "averagePrice"]))
    return round(size * price, 6) if size and price else 0.0


def _timestamp(trade: Dict) -> int:
    raw = _first(trade, ["timestamp", "timeStamp", "createdAt", "created_at", "updatedAt"], 0)
    if isinstance(raw, (int, float)):
        value = int(raw)
        return value // 1000 if value > 10_000_000_000 else value
    if isinstance(raw, str):
        if raw.isdigit():
            value = int(raw)
            return value // 1000 if value > 10_000_000_000 else value
        try:
            return int(datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp())
        except ValueError:
            return 0
    return 0


def _short(value: str, head: int = 8, tail: int = 6) -> str:
    value = str(value or "")
    return f"{value[:head]}...{value[-tail:]}" if len(value) > head + tail else value or "N/A"


def _market_url(trade: Dict) -> str:
    slug = _first(trade, ["slug", "marketSlug", "market_slug", "eventSlug", "event_slug"], "")
    if slug:
        return f"https://polymarket.com/event/{slug}"
    title = _first(trade, ["market", "title", "marketTitle", "market_title", "question", "eventTitle"], "")
    if title:
        return f"https://polymarket.com/search?query={quote(str(title))}"
    return ""


def format_whale_activity_for_telegram(trades: List[Dict], page: int = 0, page_size: int = 2) -> str:
    """
    Format recent whale trades for Telegram display.
    """
    if not trades:
        return "🏴 No recent whale trades found."

    now = int(time.time())
    normalized = sorted(trades, key=lambda item: _timestamp(item), reverse=True)
    recent = [trade for trade in normalized if not _timestamp(trade) or now - _timestamp(trade) <= POLLING_INTERVAL]
    display_trades = recent[:10] if recent else normalized[:10]
    total_pages = max(1, (len(display_trades) - 1) // page_size + 1)
    page = min(max(page, 0), total_pages - 1)
    start = page * page_size
    end = min(start + page_size, len(display_trades))
    header = "📡 *Whale Activity (last 5 min)*" if recent else "📡 *Whale Activity (recent)*"
    lines = [header, f"Page {page + 1}/{total_pages}", ""]

    for i, t in enumerate(display_trades[start:end], start + 1):
        wallet = t.get("wallet", "")
        wallet_short = _short(wallet)
        side = str(t.get("side") or t.get("type") or "TRADE").upper()
        emoji = "🟢" if side == "BUY" else "🔴"
        amount = _trade_amount(t)
        token = _first(t, ["tokenId", "tokenID", "asset", "outcome", "outcomeName"], "")
        token_short = _short(token, head=10, tail=6)
        market = _first(t, ["market", "title", "marketTitle", "market_title", "question", "eventTitle"], "")
        market_url = _market_url(t)

        # Convert timestamp to relative time
        ts = _timestamp(t)
        if ts:
            delta = int(time.time() - ts)
            if delta < 60:
                rel_time = f"{delta}s ago"
            elif delta < 3600:
                rel_time = f"{delta // 60}m ago"
            else:
                rel_time = f"{delta // 3600}h ago"
        else:
            rel_time = "recent"

        amount_text = f"${amount:,.2f}" if amount else "montant inconnu"
        lines.append(f"{i}. {emoji} *{side}* `{amount_text}`")
        lines.append(f"   Wallet: `{wallet_short}`")
        if wallet:
            lines.append(f"   🔗 https://polymarket.com/profile/{wallet}")
            lines.append(f"   ⛓️ https://polygonscan.com/address/{wallet}")
        if market:
            lines.append(f"   Market: {market[:90]}")
        if market_url:
            lines.append(f"   📌 {market_url}")
        lines.append(f"   Token/Outcome: `{token_short}`")
        lines.append(f"   ⏱️ {rel_time}")
        lines.append("")

    lines.append("Use /scan <wallet> to analyze a whale.")
    return "\n".join(lines)
