import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

import requests
from core.config import Config
from core.logger import LoggerMixin

logger = logging.getLogger(__name__)


class DataFetcher(LoggerMixin):
    """Fetches transaction data for backtesting."""
    
    def __init__(self, api_key: str, clob_client):
        self.api_key = api_key
        self.clob_client = clob_client
        self.cache = {}
    
    def download_transactions(self, address: str, days: int = 30) -> List[Dict]:
        """Download transactions for backtesting."""
        transactions = []
        try:
            # Calculate start block
            current_block = self._get_current_block()
            blocks_per_day = 43200  # ~2 sec per block
            start_block = current_block - (blocks_per_day * days)
            
            # Fetch from PolygonScan
            url = "https://api.polygonscan.com/api"
            params = {
                "module": "account",
                "action": "txlist",
                "address": address,
                "startblock": start_block,
                "endblock": current_block,
                "sort": "desc",
                "apikey": self.api_key,
            }
            
            response = requests.get(url, params=params, timeout=30)
            if response.ok:
                data = response.json()
                if data.get("status") == "1":
                    transactions = data.get("result", [])
                    logger.info(f"Downloaded {len(transactions)} transactions")
            
        except Exception as e:
            logger.error(f"Failed to download transactions: {e}")
        
        return transactions
    
    def get_current_positions(self, address: str) -> List[Dict]:
        """Get current positions from Polymarket."""
        try:
            positions = self.clob_client.get_positions(address)
            return positions if isinstance(positions, list) else []
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    def get_current_block(self) -> int:
        """Get current block number."""
        try:
            response = requests.get(
                Config.RPC_URL,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_blockNumber",
                    "params": [],
                    "id": 1,
                },
                timeout=10
            )
            if response.ok:
                result = response.json()
                return int(result.get("result", "0x0"), 16)
        except Exception as e:
            logger.error(f"Failed to get current block: {e}")
        return 0
