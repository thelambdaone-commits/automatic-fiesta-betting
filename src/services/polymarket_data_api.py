"""
Polymarket Data API Client
Official endpoint: https://data-api.polymarket.com
No API key required.
"""
import logging
import sys
from pathlib import Path
from typing import List, Dict, Optional
import requests

# Add parent directory to path (since this file is in src/services/)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

# Now import core.config as settings from services module
try:
    from core.config import Config
except ImportError:
    # Fallback for when we're in the right directory
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from core.config import Config

logger = logging.getLogger(__name__)

DATA_API_BASE = "https://data-api.polymarket.com"


def get_trades(
    user: Optional[str] = None,
    market: Optional[str] = None,
    asset: Optional[str] = None,
    limit: int = 100,
    before: Optional[str] = None,
    after: Optional[str] = None,
) -> List[Dict]:
    """
    Fetch trades from Polymarket Data API.
    
    Args:
        user: Wallet address to filter by
        market: Market conditionId to filter by
        asset: Asset token_id to filter by
        limit: Number of trades to return (max 1000)
        before: Return trades before this timestamp
        after: Return trades after this timestamp
    
    Returns:
        List of trade dictionaries with keys:
        - side (BUY/SELL)
        - size (trade size)
        - price (execution price)
        - market (conditionId)
        - asset (token_id)
        - user (wallet address)
        - timestamp
        - transactionHash
    """
    params = {"limit": min(limit, 1000)}
    if user:
        params["user"] = user
    if market:
        params["market"] = market
    if asset:
        params["asset"] = asset
    if before:
        params["before"] = before
    if after:
        params["after"] = after
    
    try:
        response = requests.get(
            f"{DATA_API_BASE}/trades",
            params=params,
            timeout=Config.REQUEST_TIMEOUT if hasattr(Config, 'REQUEST_TIMEOUT') else 20
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error("Data API trades fetch failed: %s", e)
        return []


def get_user_trades(user: str, limit: int = 100) -> List[Dict]:
    """
    Get recent trades for a specific user/wallet.
    This is the PRIMARY endpoint for copy trading detection.
    """
    return get_trades(user=user, limit=limit)


def get_market_trades(market: str, limit: int = 100) -> List[Dict]:
    """Get recent trades for a specific market."""
    return get_trades(market=market, limit=limit)


def format_trade_for_telegram(trade: Dict) -> str:
    """Format a trade dict into a readable Telegram message."""
    side = trade.get("side", "UNKNOWN")
    size = float(trade.get("size", 0) or 0)
    price = float(trade.get("price", 0) or 0)
    market = trade.get("market", "unknown")
    asset = trade.get("asset", "unknown")
    
    emoji = "🟢" if side.upper() == "BUY" else "🔴"
    
    return (
        f"{emoji} *Trade détecté*\n"
        f"Side: `{side}`\n"
        f"Size: `${size:.2f}`\n"
        f"Price: `{price:.3f}`\n"
        f"Market: `{market[:8]}...{market[-6:]}`\n"
        f"Asset: `{asset[:8]}...{asset[-6:]}`"
    )
