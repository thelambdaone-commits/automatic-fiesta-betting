import logging
from typing import Dict, Optional
from decimal import Decimal

from core.config import Config
from core.logger import LoggerMixin

logger = logging.getLogger(__name__)


class RiskGuard(LoggerMixin):
    """Risk management and trade validation."""
    
    def __init__(self, simulation: bool = True):
        self.simulation = simulation
    
    def validate_trade(self, token_id: str, side: str, amount: float) -> Dict:
        """Validate trade against risk rules."""
        result = {"valid": True, "reason": None}
        
        # Check minimum/maximum order size
        if amount < Config.MIN_ORDER_SIZE:
            result["valid"] = False
            result["reason"] = f"Amount {amount} below minimum {Config.MIN_ORDER_SIZE}"
            return result
        
        if amount > Config.MAX_ORDER_SIZE:
            result["valid"] = False  
            result["reason"] = f"Amount {amount} exceeds maximum {Config.MAX_ORDER_SIZE}"
            return result
        
        # Check slippage tolerance
        slippage = getattr(Config, 'SLIPPAGE_TOLERANCE', 0.01)
        if slippage < 0 or slippage > 0.1:  # Max 10% slippage
            result["valid"] = False
            result["reason"] = f"Invalid slippage tolerance: {slippage}"
            return result
        
        return result
    
    def check_drawdown(self, current_balance: float, initial_balance: float) -> Dict:
        """Check if drawdown limit is exceeded."""
        if initial_balance <= 0:
            return {"alert": False, "drawdown": 0}
        
        drawdown = (initial_balance - current_balance) / initial_balance
        threshold = getattr(Config, 'DRAWDOWN_THRESHOLD', 0.05)  # 5% default
        
        alert = drawdown > threshold
        return {
            "alert": alert,
            "drawdown": drawdown,
            "threshold": threshold,
            "message": f"Drawdown alert: {drawdown:.2%}" if alert else None
        }
