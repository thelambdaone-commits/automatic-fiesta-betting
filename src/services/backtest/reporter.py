import logging
from typing import Dict
import pandas as pd

from core.logger import LoggerMixin

logger = logging.getLogger(__name__)


class BacktestReporter(LoggerMixin):
    """Generates backtest reports."""
    
    def __init__(self):
        pass
    
    def save_to_csv(self, df: pd.DataFrame, output_file: str):
        """Save backtest results to CSV."""
        try:
            df.to_csv(output_file, index=False)
            logger.info(f"Saved backtest results to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save CSV: {e}")
    
    def print_summary(self, stats: Dict):
        """Print summary to console."""
        if "error" in stats:
            print(f"Error: {stats['error']}")
            return
        
        print("\n" + "="*50)
        print("BACKTEST SUMMARY")
        print("="*50)
        print(f"Total Trades: {stats.get('total_trades', 0)}")
        print(f"Winning Trades: {stats.get('winning_trades', 0)}")
        print(f"Losing Trades: {stats.get('losing_trades', 0)}")
        print(f"Win Rate: {stats.get('win_rate', 0):.2%}")
        print(f"Total PnL: ${stats.get('total_pnl', 0):.2f}")
        print(f"Max Drawdown: ${stats.get('max_drawdown', 0):.2f}")
        print(f"Sharpe Ratio: {stats.get('sharpe_ratio', 0):.2f}")
        print(f"Profit Factor: {stats.get('profit_factor', 0):.2f}")
        print("="*50 + "\n")
    
    def generate_html_report(self, stats: Dict, df: pd.DataFrame) -> str:
        """Generate HTML report (simplified)."""
        return f"""
        <html>
        <head><title>Backtest Report</title></head>
        <body>
            <h1>Backtest Report</h1>
            <p>Total Trades: {stats.get('total_trades', 0)}</p>
            <p>Win Rate: {stats.get('win_rate', 0):.2%}</p>
            <p>Total PnL: ${stats.get('total_pnl', 0):.2f}</p>
        </body>
        </html>
        """
