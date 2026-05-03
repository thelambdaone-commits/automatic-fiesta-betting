import asyncio
import logging
import os
import sys
import time
from decimal import Decimal
from typing import Dict, List, Optional

import requests
from eth_account import Account
from core.config import Config, get_proxies
from utils.utils import get_target_position_size

# Add parent directory to path for internal imports
sys.path.insert(0, Config._base_dir())

from _py_clob_client.client import ClobClient
from _py_clob_client.clob_types import ApiCreds, MarketOrderArgs, OrderArgs, OrderType, BalanceAllowanceParams, AssetType
from _py_clob_client.order_builder.constants import BUY as SIDE_BUY, SELL as SIDE_SELL
from _py_clob_client.constants import POLYGON

# JSONL logger
from services.jsonl_logger import log_trade as jsonl_log_trade
from services.smart_copy import apply_profile_to_amount, apply_adaptive_profile, get_profile

# Initialize configuration
Config.validate()

# API credentials
creds = ApiCreds(
    api_key=Config.API_KEY,
    api_secret=Config.SECRET,
    api_passphrase=Config.PASSPHRASE,
)

# Test mode configuration
TEST_MIN_ORDER = Config.TEST_MIN_ORDER
TEST_MAX_ORDER = Config.TEST_MAX_ORDER
TEST_DELAY = Config.TEST_DELAY

# Production mode configuration
PROD_MIN_ORDER = Config.PROD_MIN_ORDER
PROD_MAX_ORDER = Config.PROD_MAX_ORDER
PROD_DELAY = Config.PROD_DELAY

logger = logging.getLogger(__name__)


class PolymarketTrader:
    def __init__(self, mode: str = 'prod'):
        """
        Args:
            mode: 'test' for test mode, 'prod' for production mode
        """
        self.mode = mode
        self.min_order = TEST_MIN_ORDER if mode == 'test' else PROD_MIN_ORDER
        self.max_order = TEST_MAX_ORDER if mode == 'test' else PROD_MAX_ORDER
        self.delay = TEST_DELAY if mode == 'test' else PROD_DELAY
        self.simulation = mode in {"test", "sim", "simulation", "paper"} or Config.SIMULATION_MODE or not Config.LIVE_TRADING
        self.wallet_address = Account.from_key(Config.PRIVATE_KEY).address
        
        # SECURITY: Live trading validation
        if not self.simulation:
            if not Config.CONFIRM_LIVE_TRADING:
                logger.critical(
                    "🚨 LIVE TRADING MODE requires CONFIRM_LIVE_TRADING=true in .env"
                )
                logger.critical(
                    "🚨 Set CONFIRM_LIVE_TRADING=true to proceed with live trading"
                )
                raise RuntimeError(
                    "Live trading not confirmed. Set CONFIRM_LIVE_TRADING=true in .env"
                )
            
            # Additional safety checks for live trading
            if Config.LIVE_TRADING and not Config.CONFIRM_LIVE_TRADING:
                logger.warning(
                    "⚠️ LIVE_TRADING is enabled but not confirmed. Use CONFIRM_LIVE_TRADING=true"
                )
            
            logger.warning(
                "🔴 LIVE TRADING MODE ENABLED - Real funds will be used!"
            )
            logger.warning(
                f"🔴 Wallet: {self.wallet_address}"
            )
            logger.warning(
                f"🔴 Min order: {self.min_order} USDC | Max order: {self.max_order} USDC"
            )
        else:
            logger.info(
                "🟢 SIMULATION MODE - No real funds will be used"
            )
        
        self.client = ClobClient(
            host=Config.HOST,
            key=Config.PRIVATE_KEY, 
            chain_id=Config.CHAIN_ID,
            creds=creds
        )
        
        # Telegram config for multi-chat notifications
        self.telegram_token = getattr(Config, 'TELEGRAM_BOT_TOKEN', None)
        chat_id_str = str(getattr(Config, 'TELEGRAM_CHAT_ID', '') or '')
        self.telegram_chat_ids = [cid.strip() for cid in chat_id_str.split(',') if cid.strip()]
    
    def send_telegram_notification(self, message: str):
        """Send notification to all configured Telegram chat IDs."""
        if not self.telegram_token or not self.telegram_chat_ids:
            return
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        
        for chat_id in self.telegram_chat_ids:
            try:
                payload["chat_id"] = chat_id
                response = requests.post(url, json=payload, timeout=10)
                response.raise_for_status()
                logger.info(f"Telegram notification sent to {chat_id}")
            except Exception as e:
                logger.error(f"Failed to send Telegram notification to {chat_id}: {e}")

    def check_cash_balance(self):
        """Fetch USDC balance using web3"""
        try:
            balance_info = self.client.get_balance_allowance(
                    params=BalanceAllowanceParams(
                        asset_type=AssetType.COLLATERAL
                            )
                )
            return balance_info
            
        except Exception as e:
            logger.error(f"Failed to query balance: {e}")
            return None

    @staticmethod
    def normalize_side(side) -> str:
        if side in (0, "0", SIDE_BUY):
            return SIDE_BUY
        if side in (1, "1", SIDE_SELL):
            return SIDE_SELL
        raise ValueError(f"Unsupported order side: {side}")

    async def place_order(self, token_id: str, direction: str, amount: float) -> Dict:
        """
        Place an order with specified parameters
        
        Args:
            token_id: Market identifier
            direction: Order direction (BUY/SELL)
            amount: Order amount (USDC amount for BUY, shares for SELL)
        """
        try:
            direction = self.normalize_side(direction)
            
            # Note: Balance/Position checks are now done in execute_trade for better control

            # create a market order
            order_args = MarketOrderArgs(
                token_id=token_id,
                amount=amount,
                side=direction
            )
            signed_order = self.client.create_market_order(order_args)
            response = self.client.post_order(signed_order)
            
            logger.info(f"{direction} Order placed successfully: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to place order: {str(e)}")
            raise

    async def execute_trade(self, trade_data: Dict):
        """
        Follow a trade with risk management
        """
        try:
            # Add delay before following trade
            await asyncio.sleep(self.delay)
            
            # Extract trade details
            token_id = trade_data.get("tokenId")
            side = trade_data.get("side")
            makerAmount = Decimal(str(trade_data.get("makerAmount", 0)))
            source_wallet = trade_data.get("sourceWallet") or trade_data.get("maker") or "unknown"
            
            # Validate trade parameters
            if token_id is None or side is None or makerAmount <= 0:
                logger.error("Invalid trade data received")
                return
            side = self.normalize_side(side)
            smart_profile = get_profile(source_wallet)
            smart_simulation = bool(smart_profile and smart_profile.get("simulation", True))
            
            # === RISK MANAGEMENT & SIZE CALCULATION ===
            
            if side == "BUY":
                # 1. Check user balance
                if smart_simulation:
                    user_balance = float(smart_profile.get("portfolio_amount", 0) or 0)
                else:
                    balance_info = self.check_cash_balance()
                    if not balance_info:
                        logger.error("Unable to get balance, skipping trade")
                        return
                    user_balance = float(balance_info.get('balance', 0))
                
                # 2. Calculate trade size
                if smart_profile:
                    suggested_size = apply_adaptive_profile(source_wallet, float(makerAmount), smart_profile)
                else:
                    max_risk_percent = getattr(Config, 'MAX_RISK_PER_TRADE', 0.05)
                    suggested_size = min(
                        user_balance * max_risk_percent,
                        float(makerAmount),
                        self.max_order
                    )
                
                final_amount = max(self.min_order, suggested_size)
                
                # Check balance again
                if not smart_simulation and user_balance < final_amount:
                    logger.warning(f"Insufficient balance for BUY: {user_balance} < {final_amount}")
                    return

            else: # SELL
                # 1. Check current position
                position_shares = get_target_position_size(self.wallet_address, token_id)
                if position_shares <= 0:
                    logger.info(f"No position to sell for {token_id}, skipping")
                    return
                
                # 2. Calculate sell size
                # For SELL, makerAmount from leader is shares.
                # If leader sells X shares, we try to sell X shares, capped by our position.
                if smart_profile:
                    # Scaling for smart profiles might be different, but for now we cap to position
                    suggested_size = apply_adaptive_profile(source_wallet, float(makerAmount), smart_profile)
                else:
                    # Simple mirror: try to sell what leader sold, but cap to our position
                    suggested_size = float(makerAmount)
                
                final_amount = min(suggested_size, position_shares)
                if final_amount <= 0:
                    return

            # 3. Check slippage
            slippage_tolerance = getattr(Config, 'SLIPPAGE_TOLERANCE', 0.02)
            # (Note: Slippage check is advisory here, clob-client handles actual execution)
            
            # 4. Check liquidity (minimum required)
            # TODO: Add liquidity check via Polymarket API
            # if liquidity < min_liquidity: skip_trade()
            
            # 5. Skip if wallet is all-in (would be too risky)
            # TODO: Detect if source wallet is all-in on a position
            
            # 6. Check if price pumped recently (avoid buying tops)
            # TODO: Add price movement check
            
            # 7. Simulate trade first (dry run)
            logger.info(f"🧪 Simulating trade: {side} {final_amount} {'USDC' if side == 'BUY' else 'shares'} for {token_id}")
            if self.simulation or smart_simulation:
                logger.info("Simulation mode active; not posting live order")
                self.send_telegram_notification(
                    "*🧪 Copytrade simulé*\n\n"
                    f"Wallet source: `{source_wallet}`\n"
                    f"Profil smart: `{smart_profile.get('name') if smart_profile else 'standard'}`\n"
                    f"Token: `{str(token_id)[:8]}...{str(token_id)[-6:]}`\n"
                    f"Side: {side}\n"
                    f"Amount: {final_amount} {'USDC' if side == 'BUY' else 'shares'}\n"
                    "Status: Dry-run, aucun ordre live envoyé"
                )
                jsonl_log_trade(
                    wallet=source_wallet,
                    market=token_id,
                    token_id=token_id,
                    side=side,
                    size=float(final_amount),
                    price=0.0,
                    slippage=slippage_tolerance,
                    success=True,
                    pnl=0.0
                )
                return {
                    "status": "simulated",
                    "source_wallet": source_wallet,
                    "token_id": token_id,
                    "side": side,
                    "amount": float(final_amount),
                    "smart_profile": smart_profile.get("name") if smart_profile else None,
                }
            
            # 8. Place the market order
            # SECURITY: Double-check simulation mode before live order
            if self.simulation:
                logger.error(
                    "🛑 Security check failed: Attempted live order in simulation mode!"
                )
                return
            
            order_response = await self.place_order(
                token_id=token_id,
                direction=side,
                amount=float(final_amount)
            )
            
            # Send Telegram notification to all chat IDs
            if order_response:
                side_emoji = "🔵 BUY" if side == SIDE_BUY else "🟠 SELL"
                notify_msg = (
                    f"{side_emoji} *Trade Copied!*\n\n"
                    f"Wallet source: `{source_wallet}`\n"
                    f"Token: `{token_id[:8]}...{token_id[-6:]}`\n"
                    f"Side: {side}\n"
                    f"Amount: {final_amount} {'USDC' if side == 'BUY' else 'shares'}\n"
                    f"Status: Success"
                )
                self.send_telegram_notification(notify_msg)
            
            # Check drawdown alert for Smart Copy profiles
            if smart_profile:
                self.check_drawdown_alert(smart_profile)
            
            # Log to JSONL
                jsonl_log_trade(
                    wallet=source_wallet,
                    market=token_id,
                    token_id=token_id,
                    side=side,
                    size=float(final_amount),
                    price=0.0,  # Price not available from order response directly
                    slippage=slippage_tolerance,
                    success=True,
                    pnl=0.0
                )
            
            logger.info(f"✅ Market order placed successfully: {order_response}")
            
        except Exception as e:
            logger.error(f"Error following trade: {str(e)}")

    async def close(self):
        """
        Clean up resources
        """ 
        close = getattr(self.client, "close", None)
        if close:
            result = close()
            if hasattr(result, "__await__"):
                await result

    def check_drawdown_alert(self, profile: Dict) -> None:
        """
        Vérifie si le drawdown > 10% du portfolio simulé.
        Envoie une alerte Telegram si nécessaire.
        """
        try:
            from services.jsonl_logger import get_wallet_streak
            from services.smart_copy import load_profiles
            
            wallet = profile.get("wallet")
            portfolio = float(profile.get("portfolio_amount", 0) or 0)
            
            if portfolio <= 0:
                return
            
            # Calculer P&L total depuis le début
            streak_data = get_wallet_streak(wallet, limit=1000)
            total_pnl = streak_data.get("last_10_pnl", 0)  # Approximation
            
            # Calculer drawdown en %
            drawdown_pct = abs(min(0, total_pnl)) / portfolio * 100
            
            if drawdown_pct > 10:
                alert_msg = (
                    f"⚠️ *ALERTE DRAWDOWN*\n\n"
                    f"Profil: `{profile.get('name', 'Smart Copy')}`\n"
                    f"Wallet: `{wallet}`\n"
                    f"Portfolio initial: `${portfolio:.2f}`\n"
                    f"Drawdown actuel: `{drawdown_pct:.1f}%`\n\n"
                    f"Le drawdown dépasse 10%. "
                    f"Considérez réduire l'exposition ou passer en pause."
                )
                
                self.send_telegram_notification(alert_msg)
                logger.warning(f"Drawdown alert sent for {wallet}: {drawdown_pct:.1f}%")
                
        except Exception as e:
            logger.debug("Drawdown check failed: %s", e)
