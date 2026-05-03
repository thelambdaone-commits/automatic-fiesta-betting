import logging
from typing import Dict, List

from core.logger import LoggerMixin

logger = logging.getLogger(__name__)


class WalletScorer(LoggerMixin):
    """Scores and ranks wallets based on performance."""
    
    def score_wallet(self, scan_result: Dict) -> Dict:
        """Calculate overall score for a wallet."""
        stats = scan_result.get("stats", {})
        specialization = scan_result.get("specialization", {})
        
        # Base score from win rate and volume
        win_rate = stats.get("win_rate", 0)
        volume = stats.get("total_volume_usdc", 0)
        trades = stats.get("total_trades", 0)
        
        score = 0.0
        
        # Win rate component (0-40 points)
        score += win_rate * 40
        
        # Volume component (0-30 points)
        if volume >= 100000:
            score += 30
        elif volume >= 10000:
            score += 20
        elif volume >= 1000:
            score += 10
            
        # Activity component (0-20 points)
        if trades >= 100:
            score += 20
        elif trades >= 50:
            score += 15
        elif trades >= 10:
            score += 10
            
        # Specialization bonus (0-10 points)
        confidence = specialization.get("confidence", 0)
        score += confidence * 10
        
        return {
            "total_score": min(100, score),
            "components": {
                "win_rate_score": win_rate * 40,
                "volume_score": min(30, volume / 10000),
                "activity_score": min(20, trades / 5),
                "specialization_bonus": confidence * 10,
            }
        }
    
    def rank_wallets(self, scan_results: List[Dict]) -> List[Dict]:
        """Rank multiple wallets by score."""
        scored = []
        for result in scan_results:
            score_data = self.score_wallet(result)
            scored.append({
                **result,
                "score": score_data["total_score"],
                "score_components": score_data["components"],
            })
        
        # Sort by score descending
        return sorted(scored, key=lambda x: x["score"], reverse=True)
