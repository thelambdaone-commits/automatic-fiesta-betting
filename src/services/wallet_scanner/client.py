import logging
from typing import Dict, List, Optional

import requests
from core.config import Config
from core.logger import LoggerMixin

logger = logging.getLogger(__name__)


class WalletScannerClient(LoggerMixin):
    """Handles API calls to Polymarket and PolygonScan."""
    
    def __init__(self):
        self.gamma_host = Config.GAMMA_API_HOST.rstrip('/')
        self.polygon_api_key = Config.POLYGONSCAN_API_KEY
        
    def fetch_profile(self, address: str) -> Dict:
        """Fetch wallet profile from Polymarket."""
        try:
            response = requests.get(
                f"{self.gamma_host}/public-profile",
                params={"address": address},
                timeout=10
            )
            if response.ok:
                return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch profile: {e}")
        return {}
    
    def fetch_wallet_data(self, endpoint: str, params: Dict) -> List[Dict]:
        """Fetch data from Polymarket API."""
        try:
            # Use CLOB API for orders/trades
            if endpoint in ["orders", "trades"]:
                url = f"https://clob.polymarket.com/{endpoint.lstrip('/')}"
            else:
                url = f"{self.gamma_host}/{endpoint.lstrip('/')}"
            
            response = requests.get(url, params=params, timeout=10)
            if response.ok:
                data = response.json()
                # Handle both list and dict responses
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    if 'data' in data:
                        return data['data']
                    return [data]
                return []
        except Exception as e:
            logger.error(f"Failed to fetch {endpoint}: {e}")
        return []
    
    def fetch_json(self, url: str, params: Dict, warn: bool = True) -> Dict:
        """Fetch JSON data from URL."""
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.ok:
                return response.json()
        except Exception as e:
            if warn:
                logger.warning(f"Failed to fetch {url}: {e}")
        return {}
    
    def fetch_polygonscan_data(self, address: str, start_block: int = 0) -> List[Dict]:
        """Fetch transactions from PolygonScan."""
        if not self.polygon_api_key:
            return []
            
        try:
            response = requests.get(
                "https://api.polygonscan.com/api",
                params={
                    "module": "account",
                    "action": "txlist",
                    "address": address,
                    "startblock": start_block,
                    "endblock": 99999999,
                    "sort": "desc",
                    "apikey": self.polygon_api_key
                },
                timeout=15
            )
            if response.ok:
                data = response.json()
                if data.get("status") == "1":
                    return data.get("result", [])
        except Exception as e:
            logger.error(f"PolygonScan fetch failed: {e}")
        return []
