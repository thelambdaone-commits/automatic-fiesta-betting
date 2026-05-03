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
            "stats": {},
            "specialization": {},
            "trades": [],
            "positions": [],
            "profile": {},
        }
        
        # Fetch profile
        result["profile"] = self.client.fetch_profile(address)
        
        # Try to get trades from CLOB API
        trades = self.client.fetch_wallet_data("orders", {"maker": address, "limit": 100})
        if not trades:
            trades = self.client.fetch_wallet_data("trades", {"maker": address, "limit": 100})
        
        # If no trades from API, try PolygonScan
        if not trades:
            trades = self.client.fetch_polygonscan_data(address)
        
        # Calculate stats from actual trading data
        result["stats"] = self._calculate_stats_from_trades(trades, leaderboard_pnl)
        
        # Detect specialization
        result["specialization"] = self._detect_specialization(result["stats"])
        
        # Get recent trades
        result["trades"] = self._normalize_trades(trades[:20] if trades else [])
        
        return result
    
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
    
    def _detect_specialization(self, stats: Dict) -> Dict:
        """Detect wallet specialization category."""
        trades = stats.get("total_trades", 0)
        volume = stats.get("total_volume_usdc", 0)
        win_rate = stats.get("win_rate", 0)
        
        # Simplified specialization detection
        if volume >= 100000:
            return {"category": "whale", "confidence": 0.9}
        if trades >= 50 and win_rate >= 0.55:
            return {"category": "active_profitable", "confidence": 0.7}
        if trades >= 20:
            return {"category": "active", "confidence": 0.5}
        return {"category": "new_or_low_history", "confidence": 0.3}
    
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
