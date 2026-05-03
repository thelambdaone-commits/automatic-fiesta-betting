import logging
from typing import Dict, List, Optional
import pandas as pd

from core.logger import LoggerMixin

logger = logging.getLogger(__name__)


class TransactionDecoder(LoggerMixin):
    """Decodes transaction data for backtesting."""
    
    def __init__(self, contract_abi: dict):
        self.contract_abi = contract_abi
        self.cache = {}
    
    def decode_transactions(self, transactions: list, address: str) -> pd.DataFrame:
        """Decode transaction data into DataFrame."""
        decoded = []
        
        for tx in transactions:
            try:
                decoded_tx = self._decode_single_transaction(tx, address)
                if decoded_tx:
                    decoded.append(decoded_tx)
            except Exception as e:
                logger.debug(f"Failed to decode transaction {tx.get('hash')}: {e}")
        
        return pd.DataFrame(decoded) if decoded else pd.DataFrame()
    
    def _decode_single_transaction(self, tx: dict, address: str) -> Optional[Dict]:
        """Decode a single transaction."""
        # Simplified decoding - in reality would use web3.py
        return {
            "hash": tx.get("hash", ""),
            "blockNumber": int(tx.get("blockNumber", 0)),
            "timestamp": int(tx.get("timeStamp", 0)),
            "from": tx.get("from", ""),
            "to": tx.get("to", ""),
            "value": float(tx.get("value", 0)) / 1e18,  # Convert wei to ETH
            "gas": int(tx.get("gas", 0)),
            "gasPrice": float(tx.get("gasPrice", 0)) / 1e9,  # Gwei
            "isError": tx.get("isError", "0") == "1",
            "txreceipt_status": tx.get("txreceipt_status", "1"),
        }
    
    def calculate_price(self, row: pd.Series, address: str) -> float:
        """Calculate effective price from transaction."""
        # Simplified - would use actual DEX pricing
        if row["from"].lower() == address.lower():
            # Buying
            return row["value"] / max(row.get("amount", 1), 1)
        else:
            # Selling
            return row["value"] / max(row.get("amount", 1), 1)
