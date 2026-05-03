import asyncio
import logging
import os
import sys

from decimal import Decimal
from typing import Dict
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.monitor import WalletMonitor

load_dotenv()
for proxy_key in ("HTTP_PROXY", "HTTPS_PROXY"):
    proxy_value = os.getenv(proxy_key)
    if proxy_value:
        os.environ[proxy_key] = proxy_value

from core.config import Config

TEST_WALLET = Config.TEST_WALLET

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Callback to process trade details
async def handle_trade(trade_data: Dict):
    try:
        market_id = trade_data.get("tokenId", "Unknown TokenId")
        side = trade_data.get("side", "Unknown")
        maker = trade_data.get("maker", "Unknown")
        size = Decimal(str(trade_data.get("makerAmount", 0)))

        logger.info(f"""
            Trade Details:
            -------------
            Token ID: {market_id}
            Side: {side}
            Maker: {maker}
            Size: {size}
        """)
    except Exception as e:
        logger.error(f"Error processing trade details: {str(e)}")

async def main():
    if not TEST_WALLET:
        raise ValueError("TEST_WALLET not set in config/targets/wallets.json")

    # Create monitor instance with our callback and test wallet
    monitor = WalletMonitor(handle_trade, mode='test')
    
    try:
        logger.info(f"Started monitoring test wallet: {TEST_WALLET}")
        await monitor.start()
    except KeyboardInterrupt:
        logger.info("Stopping monitor...")
        await monitor.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program stopped by user")
