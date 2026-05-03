import logging
from typing import Dict, List
import pandas as pd

from core.logger import LoggerMixin

logger = logging.getLogger(__name__)


class BacktestAnalyzer(LoggerMixin):
    """Analyzes backtest results."""
    
    def __init__(self):
        self.results = {}
    
    def calculate_pnl_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate PnL statistics."""
        if df.empty:
            return pd.DataFrame()
        
        try:
            # Calculate cumulative PnL
            df["cumulative_pnl"] = df["pnl"].cumsum()
            
            # Calculate drawdown
            df["peak"] = df["cumulative_pnl"].cummax()
            df["drawdown"] = df["peak"] - df["cumulative_pnl"]
            
            return df
        except Exception as e:
            logger.error(f"Failed to calculate PnL stats: {e}")
            return df
    
    def calculate_summary(self, df: pd.DataFrame) -> Dict:
        """Generate summary statistics."""
        if df.empty:
            return {"error": "No data"}
        
        try:
            total_trades = len(df)
            winning_trades = len(df[df["pnl"] > 0])
            losing_trades = len(df[df["pnl"] <= 0])
            
            return {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": winning_trades / max(total_trades, 1),
                "total_pnl": float(df["pnl"].sum()),
                "max_drawdown": float(df["drawdown"].max()),
                "sharpe_ratio": self._calculate_sharpe(df),
                "profit_factor": self._calculate_profit_factor(df),
            }
        except Exception as e:
            logger.error(f"Failed to calculate summary: {e}")
            return {"error": str(e)}
    
    def _calculate_sharpe(self, df: pd.DataFrame) -> float:
        """Calculate Sharpe ratio."""
        if df.empty or "pnl" not in df.columns:
            return 0.0
        
        returns = df["pnl"].pct_change().dropna()
        if len(returns) < 2:
            return 0.0
        
        return float(returns.mean() / returns.std()) if returns.std() > 0 else 0.0
    
    def _calculate_profit_factor(self, df: pd.DataFrame) -> float:
        """Calculate profit factor."""
        gross_profit = df[df["pnl"] > 0]["pnl"].sum()
        gross_loss = abs(df[df["pnl"] < 0]["pnl"].sum())
        
        return float(gross_profit / gross_loss) if gross_loss > 0 else float('inf')
