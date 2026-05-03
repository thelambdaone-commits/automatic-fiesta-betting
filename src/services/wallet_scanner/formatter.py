import logging
from typing import Dict, List

from core.logger import LoggerMixin

logger = logging.getLogger(__name__)


class WalletFormatter(LoggerMixin):
    """Formats wallet analysis results for display."""
    
    def format_report(self, result: Dict) -> str:
        """Format complete wallet analysis report."""
        address = result.get("address", "unknown")
        stats = result.get("stats", {})
        specialization = result.get("specialization", {})
        score = result.get("score", 0)
        
        lines = [
            f"*📊 Analyse Wallet: {address[:8]}...{address[-6:]}*",
            "",
            "*Statistiques publiques*",
            f"• Total trades: `{stats.get('total_trades', 0)}`",
            f"• Win rate: `{stats.get('win_rate', 0):.1%}`",
            f"• Volume: `${stats.get('total_volume_usdc', 0):.2f}` USDC",
            f"• Portfolio: `${stats.get('portfolio_value', 0):.2f}` USDC",
            "",
            "*Spécialisation*",
            f"• Catégorie: `{specialization.get('category', 'unknown')}`",
            f"• Confiance: `{specialization.get('confidence', 0):.0%}`",
        ]
        
        if score > 0:
            lines.extend([
                "",
                "*Score global*",
                f"• Score: `{score}/100`",
            ])
        
        return "\n".join(lines)
    
    def format_short_summary(self, scan_result: Dict) -> str:
        """Format short summary for lists."""
        address = scan_result.get("address", "")
        stats = scan_result.get("stats", {})
        pnl = stats.get("leaderboard_pnl")
        
        summary = f"`{address[:8]}...{address[-6:]}`"
        summary += f" | Trades: `{stats.get('total_trades', 0)}`"
        summary += f" | WR: `{stats.get('win_rate', 0):.0%}`"
        
        if pnl is not None:
            summary += f" | PnL: `${pnl:.2f}`"
            
        return summary
    
    def format_market_url(self, token_id: str) -> str:
        """Generate Polymarket market URL."""
        return f"https://polymarket.com/market/{token_id}"
    
    def format_wallet_url(self, address: str) -> str:
        """Generate Polymarket profile URL."""
        return f"https://polymarket.com/profile/{address}"
