import os
import json
import logging
import sys
import pandas as pd
from datetime import datetime
from pprint import pprint

from core.config import Config
from _py_clob_client.client import ClobClient
from _py_clob_client.clob_types import ApiCreds
from _py_clob_client.constants import POLYGON
from services.backtest import WalletBacktest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_polymarket_transactions(address: str, output_file: str):
    """
    Get all USDC token transfers for an address and save to CSV
    
    Args:
        address: The address to get transactions for
        output_file: Output CSV file name
    """
    # Initialize ClobClient
    creds = ApiCreds(
        api_key=Config.API_KEY,
        api_secret=Config.SECRET,
        api_passphrase=Config.PASSPHRASE,
    )
    client = ClobClient(
        host=Config.HOST,
        key=Config.PRIVATE_KEY, 
        chain_id=Config.CHAIN_ID,
        creds=creds
    )
    
    # Initialize WalletBacktest
    backtest = WalletBacktest(Config.POLYGONSCAN_API_KEY, client)
    
    # Download all transactions
    # print(f"Downloading target transactions for {address}...")
    transactions = backtest.download_transactions(address)
    
    if not transactions:
        print("No target transactions found")
        return
    
    # Process transactions and save to CSV
    df = backtest.process_transactions(transactions, address)
    backtest.save_to_csv(df, output_file)


def main():
    counter = 0
    now = datetime.now()

    target_wallets_file = os.getenv('TARGET_WALLETS_FILE', str(Config.TARGETS_FILE))
    if not target_wallets_file or not os.path.exists(target_wallets_file):
        logger.error("TARGET_WALLETS_FILE not set or file not found")
        return

    if target_wallets_file.endswith(".json"):
        with open(target_wallets_file, "r", encoding="utf-8") as file:
            wallets_config = json.load(file)
        wallets = wallets_config.get("backtest_wallets") or wallets_config.get("copytrade_wallets", [])
    else:
        wallets_df = pd.read_csv(target_wallets_file)
        wallets = wallets_df["wallet"].dropna().tolist()
    
    # Process each wallet address
    for wallet in wallets:
        counter += 1
        print(f"\nProcessing wallet: {wallet} || ({counter}/{len(wallets)})")
        Config.BACKTEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_file = str(Config.BACKTEST_OUTPUT_DIR / f"{wallet}.csv")
        try:
            get_polymarket_transactions(wallet, output_file)
        except Exception as e:
            print(f"Error processing wallet {wallet}: {e}")
            continue

    logger.info(f"Total time: {datetime.now() - now}")

if __name__ == "__main__":
    main()
