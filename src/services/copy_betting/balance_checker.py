import logging
from typing import Dict, Optional

from core.config import Config
from core.logger import LoggerMixin

logger = logging.getLogger(__name__)


class BalanceChecker(LoggerMixin):
    """Handles balance checks and validation."""
    
    def __init__(self, client):
        self.client = client
    
    def check_cash_balance(self) -> Optional[Dict]:
        """Check USDC balance."""
        try:
            balance_info = self.client.get_balance_allowance(
                params={"asset_type": "COLLATERAL"}
            )
            if balance_info:
                logger.info(f"Balance check: {balance_info}")
            return balance_info
        except Exception as e:
            logger.error(f"Failed to check balance: {e}")
            return None
    
    def validate_sufficient_balance(self, amount: float) -> bool:
        """Check if balance is sufficient for trade."""
        balance_info = self.check_cash_balance()
        if not balance_info:
            return False
        
        available = float(balance_info.get('balance', 0))
        if available < amount:
            logger.warning(f"Insufficient balance: {available} < {amount}")
            return False
        return True
