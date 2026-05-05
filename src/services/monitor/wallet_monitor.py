import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.config import Config, get_proxies
import websockets
from web3 import Web3
from web3.middleware import geth_poa_middleware

logger = logging.getLogger(__name__)

TARGET_REFRESH_SECONDS = 30

# Exponential backoff parameters
BACKOFF_INITIAL = 1      # Initial delay in seconds
BACKOFF_MAX = 60         # Maximum delay in seconds
BACKOFF_MULTIPLIER = 2   # Multiply delay by this after each failure


class WalletMonitor:
    def __init__(self, on_trade_callback: Callable, mode: str = 'prod'):
        """
        params:
            on_trade_callback: Callback function to handle detected trades
            mode: 'test' for test wallet, 'prod' for target wallet (default: 'prod')
        """
        self.mode = mode
        self._last_target_refresh = 0.0
        wallet_addresses = self._configured_wallets(mode)

        if not wallet_addresses:
            raise ValueError(f"No wallet address configured for {mode} mode")

        self._set_target_wallets(wallet_addresses)
        logger.info("Monitoring in %s mode for %d wallet(s): %s", mode, len(self.target_wallets), ", ".join(self.target_wallets))
        
        # Use Polygon WebSocket URL
        self.ws_url = Config.WS_URL
        self.web3 = Web3(Web3.WebsocketProvider(self.ws_url))
        # Add PoS middleware
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.on_trade_callback = on_trade_callback
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        self.paused = False  # Pause state for copy trading
        self.message_count = 0
        self._control_file = Config.DATA_DIR / "bot_control.json"
        self._heartbeat_file = Config.DATA_DIR / "monitor_heartbeat.json"
        Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._control_file = Config.DATA_DIR / "bot_control.json"
        self._heartbeat_file = Config.DATA_DIR / "monitor_heartbeat.json"
        Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Get matchOrders signature from config
        self.match_orders_signature = Config.MATCH_ORDERS_SIGNATURE
        if not self.match_orders_signature.startswith('0x'):
            self.match_orders_signature = '0x' + self.match_orders_signature
        self.match_orders_signature = self.match_orders_signature.lower()
        
        # Load contract ABI
        try:
            abi_path = Path(__file__).resolve().parents[2] / 'abi' / 'NegRiskFeeModule.json'
            logger.info("Loading ABI from: %s", abi_path)
            
            with open(abi_path, 'r') as f:
                self.contract_abi = json.load(f)
                
                # Find matchOrders function ABI
                self.match_orders_abi = next(
                    (item for item in self.contract_abi 
                    if item.get('type') == 'function' and item.get('name') == 'matchOrders'),
                    None
                )
                
                if self.match_orders_abi is None:
                    raise ValueError("matchOrders function not found in ABI")
                
                self.match_orders_contract = self.web3.eth.contract(
                    abi=[self.match_orders_abi]
                )
                
        except Exception as e:
            logger.error("Error loading ABI: %s", str(e))
            raise

    @staticmethod
    def _configured_wallets(mode: str) -> List[str]:
        configured_targets = WalletMonitor._configured_target_wallets()
        smart_copy_targets = WalletMonitor._smart_copy_wallets()

        if mode in {"test", "sim", "simulation", "paper"}:
            wallets = ([Config.TEST_WALLET] if Config.TEST_WALLET else []) + configured_targets + smart_copy_targets
        else:
            wallets = configured_targets
            if not wallets and Config.TARGET_WALLET:
                wallets = [Config.TARGET_WALLET]
            wallets += smart_copy_targets

        return WalletMonitor._normalize_wallets(wallets)

    @staticmethod
    def _configured_target_wallets() -> List[str]:
        wallets = list(Config.TARGET_WALLETS or [])
        try:
            if Config.TARGETS_FILE.exists():
                with Config.TARGETS_FILE.open("r", encoding="utf-8") as file:
                    data = json.load(file)
                wallets = data.get("wallet_mirror_wallets") or data.get("copytrade_wallets") or wallets
        except Exception as e:
            logger.debug("Unable to reload target wallets: %s", e)
        return list(wallets or [])

    @staticmethod
    def _smart_copy_wallets() -> List[str]:
        path = Config.CONFIG_DIR / "targets" / "smart_copy_profiles.json"
        try:
            if not path.exists():
                return []
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            profiles = data.get("profiles", data)
            if not isinstance(profiles, dict):
                return []
            return [
                str(profile.get("wallet") or "")
                for profile in profiles.values()
                if isinstance(profile, dict) and profile.get("wallet") and profile.get("enabled", True)
            ]
        except Exception as e:
            logger.debug("Unable to reload Smart Copy wallets: %s", e)
            return []

    @staticmethod
    def _normalize_wallets(wallets: List[str]) -> List[str]:
        normalized = []
        seen = set()
        for wallet in wallets:
            wallet = (wallet or "").strip()
            if not wallet:
                continue
            key = wallet.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(wallet)
        return normalized

    def _set_target_wallets(self, wallet_addresses: List[str]) -> None:
        self.target_wallets = [Web3.to_checksum_address(wallet) for wallet in wallet_addresses]
        self.target_wallets_lower = {wallet.lower() for wallet in self.target_wallets}
        self.target_wallet = self.target_wallets[0]
        self.target_wallet_lower = self.target_wallet.lower()

    def is_paused(self) -> bool:
        """Check if trading is paused (via file or internal state)."""
        if self._control_file.exists():
            try:
                with open(self._control_file, 'r') as f:
                    control = json.load(f)
                    self.paused = control.get("paused", False)
            except Exception:
                pass
        return self.paused

    def set_paused(self, paused: bool) -> None:
        """Set pause state and write to control file."""
        self.paused = paused
        try:
            with open(self._control_file, 'w') as f:
                json.dump({"paused": paused, "timestamp": time.time()}, f)
        except Exception as e:
            logger.error("Failed to write control file: %s", e)

    def refresh_configured_wallets(self, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self._last_target_refresh < TARGET_REFRESH_SECONDS:
            return
        self._last_target_refresh = now

        wallet_addresses = self._configured_wallets(self.mode)
        if not wallet_addresses:
            logger.warning("No configured wallet remains for %s mode; keeping current monitor targets", self.mode)
            return

        next_targets = {Web3.to_checksum_address(wallet).lower() for wallet in wallet_addresses}
        if next_targets == self.target_wallets_lower:
            return

        self._set_target_wallets(wallet_addresses)
        logger.info(
            "Refreshed monitor targets in %s mode: %d wallet(s): %s",
            self.mode,
            len(self.target_wallets),
            ", ".join(self.target_wallets),
        )

    def is_paused(self) -> bool:
        """Check if trading is paused (via file or internal state)."""
        # Check control file
        if self._control_file.exists():
            try:
                with open(self._control_file, 'r') as f:
                    control = json.load(f)
                    self.paused = control.get("paused", False)
            except Exception:
                pass
        return self.paused

    def set_paused(self, paused: bool) -> None:
        """Set pause state and write to control file."""
        self.paused = paused
        try:
            with open(self._control_file, 'w') as f:
                json.dump({"paused": paused, "timestamp": time.time()}, f)
        except Exception as e:
            logger.error("Failed to write control file: %s", e)

    # Decode input data
    def decode_match_orders(self, input_data: str) -> Optional[Dict]:
        """Decode matchOrders function input data"""
        try:
            # Decode parameters
            decoded = self.match_orders_contract.decode_function_input(input_data)
            
            # decoded is a tuple of (function_name, parameters)
            _, params = decoded
            taker_order = params['takerOrder']
            
            return {
                "maker": taker_order['maker'],
                "makerAmount": taker_order['makerAmount'],
                "tokenId": taker_order['tokenId'],
                "side": taker_order['side']
            }
            
        except Exception as e:
            logger.debug("Error decoding matchOrders data: %s", str(e))
            return None

    # Process incoming WebSocket message
    async def process_message(self, message: str):
        """
        params:
            message: Raw WebSocket message
        """
        try:
            self.refresh_configured_wallets()
            
            # Check if paused
            if self.is_paused():
                logger.debug("Trading is paused, skipping trade processing")
                return
            
            data = json.loads(message)
            if "params" in data and "result" in data["params"]:
                tx_data = await self._resolve_transaction(data["params"]["result"])
                if not tx_data:
                    return

                tx_hash = tx_data.get("hash", "unknown")
                input_data = tx_data.get("input", "")
                if isinstance(input_data, bytes):
                    input_data = "0x" + input_data.hex()
                input_data = str(input_data).lower()
                
                # Check if matchOrders call
                if input_data.startswith(self.match_orders_signature):
                    logger.info("MatchOrders TX detected: %s", tx_hash)
                    decoded_data = self.decode_match_orders(input_data)
                    
                    if decoded_data and decoded_data["maker"].lower() in self.target_wallets_lower:
                        decoded_data["sourceWallet"] = decoded_data["maker"]
                        logger.info(
                            "Target wallet matchOrders detected: TX Hash: %s, Maker: %s, Amount: %s, Token: %s, Side: %s",
                            tx_hash,
                            decoded_data["maker"],
                            decoded_data["makerAmount"],
                            decoded_data["tokenId"],
                            "BUY" if decoded_data["side"] == 0 else "SELL"
                        )
                        await self.on_trade_callback(decoded_data)
                    else:
                        logger.debug("MatchOrders TX detected (not target): %s", tx_hash)
                        
        except json.JSONDecodeError:
            logger.error("Failed to decode WebSocket message: %s", message)
        except Exception as e:
            logger.error("Error processing message: %r", e)

    async def _resolve_transaction(self, tx_result) -> Optional[Dict]:
        """Normalize pending transaction subscription payloads."""
        if isinstance(tx_result, dict):
            return tx_result
        if isinstance(tx_result, str):
            try:
                tx = await asyncio.to_thread(lambda: self.web3.eth.get_transaction(tx_result))
                return dict(tx) if tx else None
            except Exception as e:
                logger.debug("Pending tx %s not available yet: %r", tx_result, e)
                return None
        logger.debug("Unsupported pending transaction payload: %r", tx_result)
        return None

    # Get current block height from Polygon
    async def get_block_height(self):
        """Get current block height from Polygon network"""
        try:
            block_number = await asyncio.to_thread(lambda: self.web3.eth.block_number)
            return block_number
        except Exception as e:
            logger.error("Error getting block height: %s", str(e))
            return None

    # Monitor and log block height
    async def monitor_block_height(self):
        """Monitor and log block height every 5 seconds"""
        while self.running:
            try:
                block_height = await self.get_block_height()
                if block_height:
                    logger.info("Current block height: %s | Messages received: %s | Paused: %s", 
                               block_height, self.message_count, self.paused)
                
                # Write heartbeat
                heartbeat_data = {
                    "timestamp": time.time(),
                    "block_height": block_height,
                    "messages_count": self.message_count,
                    "running": self.running,
                    "paused": self.paused,
                    "ws_url": self.ws_url,
                }
                with open(self._heartbeat_file, 'w') as f:
                    json.dump(heartbeat_data, f)
                
                await asyncio.sleep(5)
            except Exception as e:
                logger.error("Error in block height monitor: %s", str(e))
                await asyncio.sleep(5)

    # Start monitoring
    async def start(self):
        self.running = True
        # Start block height monitoring in a separate task
        asyncio.create_task(self.monitor_block_height())
        
        backoff_delay = BACKOFF_INITIAL
        
        while self.running:
            try:
                logger.info("Connecting to Polygon WebSocket at %s (delay: %.1fs)", self.ws_url, backoff_delay)
                async with websockets.connect(self.ws_url) as websocket:
                    self.websocket = websocket
                    
                    # Reset backoff on successful connection
                    backoff_delay = BACKOFF_INITIAL
                    
                    # Subscribe to pending transactions (standard Ethereum WebSocket)
                    subscribe_message = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "eth_subscribe",
                        "params": ["newPendingTransactions", True]
                    }
                    
                    await websocket.send(json.dumps(subscribe_message))
                    subscription_response = await websocket.recv()
                    logger.info("Subscription response: %s", subscription_response)
                    
                    # Process incoming messages
                    while self.running:
                        message = await websocket.recv()
                        self.message_count += 1
                        await self.process_message(message)
                        
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed. Reconnecting (backoff: %.1fs)...", backoff_delay)
                await asyncio.sleep(backoff_delay)
                # Increase backoff for next attempt
                backoff_delay = min(backoff_delay * BACKOFF_MULTIPLIER, BACKOFF_MAX)
            except Exception as e:
                logger.error("Error in wallet monitor: %r (backoff: %.1fs)", e, backoff_delay)
                await asyncio.sleep(backoff_delay)
                backoff_delay = min(backoff_delay * BACKOFF_MULTIPLIER, BACKOFF_MAX)

    # Stop monitoring
    async def stop(self):
        self.running = False
        if self.websocket:
            await self.websocket.close()
