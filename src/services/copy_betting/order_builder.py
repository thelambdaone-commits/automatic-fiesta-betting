import logging
from typing import Dict, Optional
from decimal import Decimal

from _py_clob_client.clob_types import MarketOrderArgs, OrderArgs, OrderType
from core.config import Config
from core.logger import LoggerMixin

logger = logging.getLogger(__name__)


class OrderBuilder(LoggerMixin):
    """Builds and signs orders for Polymarket."""
    
    def __init__(self, client):
        self.client = client
    
    def build_market_order(self, token_id: str, side: str, amount: float) -> Optional[Dict]:
        """Build a market order."""
        try:
            # Normalize side
            normalized_side = "BUY" if side.upper() == "BUY" else "SELL"
            
            # Create order args
            order_args = MarketOrderArgs(
                token_id=token_id,
                side=normalized_side,
                amount=Decimal(str(amount))
            )
            
            # Build and sign order
            signed_order = self.client.create_or_derive_api_creds()
            return {
                "order_args": order_args,
                "signed_order": signed_order,
                "token_id": token_id,
                "side": normalized_side,
                "amount": amount
            }
        except Exception as e:
            logger.error(f"Failed to build order: {e}")
            return None
    
    def submit_order(self, signed_order) -> Dict:
        """Submit order to Polymarket."""
        try:
            response = self.client.post_order(signed_order)
            return {"success": True, "response": response}
        except Exception as e:
            logger.error(f"Failed to submit order: {e}")
            return {"success": False, "error": str(e)}
