import asyncio
import logging
import sys
import os
import json
from typing import Dict
from pathlib import Path

from core.config import Config
from services.monitor import WalletMonitor
from services.copy_trade import PolymarketTrader

Config.LOG_DIR.mkdir(parents=True, exist_ok=True)

# Load session from JSON file
session_path = Config.SESSION_FILE
if session_path.exists():
    try:
        with open(session_path, 'r') as f:
            session_data = json.load(f)
        # Update Config with session data
        Config.WS_URL = session_data.get('alchemy_ws_url', Config.WS_URL)
        Config.RPC_URL = session_data.get('rpc_url', Config.RPC_URL)
        Config.API_KEY = session_data.get('polymarket_api_key', Config.API_KEY)
        Config.SECRET = session_data.get('polymarket_api_secret', Config.SECRET)
        Config.PASSPHRASE = session_data.get('polymarket_api_passphrase', Config.PASSPHRASE)
        Config.PRIVATE_KEY = session_data.get('private_key', Config.PRIVATE_KEY)
        Config.HOST = session_data.get('host', Config.HOST)
        Config.CHAIN_ID = session_data.get('chain_id', Config.CHAIN_ID)
        logging.getLogger(__name__).info(f"Loaded session from {session_path}")
    except Exception as e:
        logging.getLogger(__name__).warning(f"Could not load session: {e}")

# Configure logging with rotation
from logging.handlers import RotatingFileHandler

# Create handlers
console_handler = logging.StreamHandler(sys.stdout)
file_handler = RotatingFileHandler(
    Config.LOG_DIR / 'polymarket_follower.log',
    maxBytes=5 * 1024 * 1024,  # 5MB per file
    backupCount=5,               # Keep 5 backup files
    encoding='utf-8'
)

# Set formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler, file_handler]
)

# Clean up large log file if it exists and is too big
log_file = Config.LOG_DIR / 'polymarket_follower.log'
if log_file.exists() and log_file.stat().st_size > 10 * 1024 * 1024:  # > 10MB
    logger = logging.getLogger(__name__)
    logger.info(f"Log file is {log_file.stat().st_size / 1024 / 1024:.1f}MB, rotation will manage it")

logger = logging.getLogger(__name__)

# Wallet Mirror follows and replicates trades from the configured target wallet.
class WalletMirror:
    def __init__(self, mode: str = 'prod'):
        self.mode = mode
        self.trader = PolymarketTrader(mode=mode)
        self.monitor = WalletMonitor(self.handle_trade, mode=mode)
        
    # Handle trades from monitored wallet
    async def handle_trade(self, trade_data: Dict):
        """
        params:
            trade_data: Trade data from the monitored wallet
        """
        logger.info(f"New trade detected: {trade_data}")
        await self.trader.execute_trade(trade_data)
        
    # Start the application
    async def start(self):
        try:  
            # Start monitoring
            logger.info(f"Starting Wallet Mirror in {self.mode} mode...")
            await self.monitor.start()
            
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        except Exception as e:
            logger.error(f"Application error: {str(e)}")
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        """Clean up resources."""
        await self.monitor.stop()
        await self.trader.close()


async def main():
    mode = os.getenv('MODE', 'prod')  # 'test' or 'prod'
    if mode == "prod" and not (Config.TARGET_WALLETS or Config.TARGET_WALLET):
        logger.warning("No prod wallet target configured; starting Wallet Mirror in test/simulation mode")
        mode = "test"
    app = WalletMirror(mode=mode)
    await app.start()


PolymarketFollower = WalletMirror


if __name__ == "__main__":
    # Set proxy from config
    os.environ['HTTP_PROXY'] = Config.HTTP_PROXY or ''
    os.environ['HTTPS_PROXY'] = Config.HTTPS_PROXY or ''
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
