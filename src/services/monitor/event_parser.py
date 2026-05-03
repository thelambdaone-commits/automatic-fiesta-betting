import json
import logging
from typing import Dict, List, Optional

from core.config import Config
from core.logger import LoggerMixin

logger = logging.getLogger(__name__)


class EventParser(LoggerMixin):
    """Parses WebSocket events from Polymarket."""
    
    def __init__(self):
        self.event_count = 0
        self.last_block = 0
    
    def parse_event(self, event_data: Dict) -> Optional[Dict]:
        """Parse a single WebSocket event."""
        try:
            self.event_count += 1
            
            # Extract basic event info
            event_type = event_data.get("type", "unknown")
            block_number = event_data.get("blockNumber", 0)
            self.last_block = max(self.last_block, block_number)
            
            if event_type == "orderFilled":
                return self._parse_order_filled(event_data)
            elif event_type == "trade":
                return self._parse_trade(event_data)
            else:
                logger.debug(f"Unknown event type: {event_type}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to parse event: {e}")
            return None
    
    def _parse_order_filled(self, event: Dict) -> Dict:
        """Parse orderFilled event."""
        return {
            "type": "orderFilled",
            "tokenId": event.get("tokenId"),
            "side": event.get("side", "BUY"),
            "maker": event.get("maker", "unknown"),
            "taker": event.get("taker", "unknown"),
            "makerAmount": float(event.get("makerAmount", 0)),
            "takerAmount": float(event.get("takerAmount", 0)),
            "blockNumber": event.get("blockNumber", 0),
        }
    
    def _parse_trade(self, event: Dict) -> Dict:
        """Parse trade event."""
        return {
            "type": "trade",
            "tokenId": event.get("tokenId"),
            "side": event.get("side", "BUY"),
            "maker": event.get("maker", "unknown"),
            "amount": float(event.get("amount", 0)),
            "price": float(event.get("price", 0)),
            "blockNumber": event.get("blockNumber", 0),
        }
    
    def get_stats(self) -> Dict:
        """Get parser statistics."""
        return {
            "events_parsed": self.event_count,
            "last_block": self.last_block,
        }
