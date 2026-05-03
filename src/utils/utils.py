import requests
from functools import lru_cache

from core.config import Config

# Session réutilisable pour optimiser les connexions
_session = requests.Session()

@lru_cache(maxsize=128)
def get_target_position_size(address, token_id): 
    """
    returns size in shares (cached)
    """
    url = f'https://data-api.polymarket.com/positions?user={address}&sizeThreshold=.1&limit=50&offset=0&sortBy=CURRENT&sortDirection=DESC'
    response = _session.get(url, timeout=Config.REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    for position in data: 
        if position['asset'] == token_id: 
            return float(position['size'])
    return 0.0

@lru_cache(maxsize=32)
def get_position_all(address): 
    """
    returns all positions (cached)
    """
    url = f'https://data-api.polymarket.com/positions?user={address}&sizeThreshold=.1&limit=50&offset=0&sortBy=CURRENT&sortDirection=DESC'
    response = _session.get(url, timeout=Config.REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()

def clear_cache():
    """Clear cached data"""
    get_target_position_size.cache_clear()
    get_position_all.cache_clear()
