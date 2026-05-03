import logging
from typing import Dict, List, Optional

from core.logger import LoggerMixin
from .client import WalletScannerClient

logger = logging.getLogger(__name__)


class WalletAnalyzer(LoggerMixin):
    """Analyzes wallet data and calculates statistics."""
    
    def __init__(self):
        self.client = WalletScannerClient()
    
    def scan_wallet(self, address: str, leaderboard_pnl: float = None) -> Dict:
        """Perform complete wallet analysis."""
        result = {
            "address": address,
            "valid": True,
            "stats": {},
            "specialization": {},
            "trades": [],
            "positions": [],
            "profile": {},
            "profile_wallet": address,
        }
        
        # Fetch profile and detect proxy wallet
        profile = self.client.fetch_profile(address)
        result["profile"] = profile
        proxy_wallet = profile.get("proxyWallet") or profile.get("proxy_wallet") or address
        result["profile_wallet"] = proxy_wallet
        
        # 1. Fetch activity from Data API (most reliable for history)
        activity = self.client.fetch_data_api("activity", {"user": proxy_wallet, "limit": 100})
        
        # 2. Fetch positions from Data API
        positions = self.client.fetch_data_api("positions", {"user": proxy_wallet, "limit": 50})
        result["positions"] = positions
        
        # 3. Fetch recent trades from CLOB (for latest timing)
        recent_trades = self.client.fetch_wallet_data("trades", {"maker": proxy_wallet, "limit": 50})
        
        # Combine data for analysis
        all_trades = recent_trades or activity
        
        # Calculate stats
        result["stats"] = self._calculate_stats(
            activity=activity,
            trades=recent_trades,
            positions=positions,
            leaderboard_pnl=leaderboard_pnl
        )
        
        # Detect specialization
        result["specialization"] = self._detect_specialization(result["stats"], all_trades)
        
        # Normalize recent trades for UI
        result["trades"] = self._normalize_trades(all_trades[:15])
        
        return result

    def _calculate_stats(self, activity: List, trades: List, positions: List, leaderboard_pnl: float = None) -> Dict:
        """Calculate statistics from combined data sources."""
        total_trades = len(activity) if len(activity) > len(trades) else len(trades)
        
        # Estimate volume from activity
        volume = 0.0
        for act in activity:
            # Data API 'activity' usually has 'amount' or 'cash'
            amt = float(act.get("amount") or act.get("cash") or act.get("value") or 0)
            volume += amt
            
        # Win rate estimation (hard from public API, but let's try)
        # If leaderboard pnl is provided, we use it as the source of truth
        
        return {
            "total_trades": total_trades,
            "win_rate": 0.0, # Will be 0 if not on leaderboard
            "total_volume_usdc": volume,
            "portfolio_value": sum(float(p.get("currentValue") or 0) for p in positions),
            "leaderboard_pnl": leaderboard_pnl,
        }
    
    def _calculate_stats_from_trades(self, trades: List[Dict], leaderboard_pnl: float = None) -> Dict:
        """Calculate statistics from actual trades."""
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "total_volume_usdc": 0.0,
                "portfolio_value": 0.0,
                "leaderboard_pnl": leaderboard_pnl,
            }
        
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if float(t.get("price", 0) > 0.5))  # Simplified win calculation
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_volume = sum(float(t.get("makerAmount", 0) or 0) for t in trades)
        
        return {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "total_volume_usdc": total_volume,
            "portfolio_value": float(trades[0].get("balance", 0) if trades else 0),
            "leaderboard_pnl": leaderboard_pnl,
        }
    
    def _detect_specialization(self, stats: Dict, trades: List[Dict]) -> Dict:
        """Detect wallet specialization category by looking at market titles."""
        if not trades:
            return {"category": "inconnue", "confidence": 0}
            
        # Keywords for categorization
        categories = {
            "politique": ["election", "president", "trump", "biden", "poll", "house", "senate"],
            "crypto": ["bitcoin", "btc", "eth", "solana", "crypto", "fed", "rate"],
            "sport": ["nba", "nfl", "soccer", "football", "tennis", "ufc"],
            "macro/news": ["inflation", "war", "news", "world", "china"],
        }
        
        # Join all market titles
        titles = " ".join([str(t.get("title") or t.get("marketTitle") or "").lower() for t in trades])
        
        counts = {cat: sum(titles.count(kw) for kw in kws) for cat, kws in categories.items()}
        top_cat = max(counts, key=counts.get)
        
        if counts[top_cat] > 0:
            return {"category": top_cat, "confidence": 0.7}
            
        return {"category": "diversifié", "confidence": 0.4}
    
    def _normalize_trades(self, rows: List[Dict]) -> List[Dict]:
        """Normalize trade data format."""
        normalized = []
        for row in rows:
            normalized.append({
                "token_id": row.get("tokenId", ""),
                "side": row.get("side", ""),
                "amount": float(row.get("makerAmount", 0) or 0),
                "timestamp": row.get("timestamp", 0),
            })
        return normalized
