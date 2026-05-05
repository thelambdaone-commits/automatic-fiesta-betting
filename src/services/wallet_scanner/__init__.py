"""Wallet scanner module and backward-compatible facade."""

import re
from typing import Dict, List

import requests

from core.config import Config, get_proxies
from .client import WalletScannerClient
from .analyzer import WalletAnalyzer
from .scorer import WalletScorer
from .formatter import WalletFormatter


class WalletScanner:
    """Facade kept for callers that used the pre-package WalletScanner API."""

    def __init__(self):
        self.client = WalletScannerClient()
        self.analyzer = WalletAnalyzer()
        self.scorer = WalletScorer()
        self.formatter = WalletFormatter()

    def _is_valid_address(self, address: str) -> bool:
        return bool(re.fullmatch(r"0x[a-fA-F0-9]{40}", str(address or "")))

    def _fetch(self, endpoint: str, params: Dict) -> object:
        base = Config.GAMMA_API_HOST if endpoint == "public-profile" else Config.DATA_API_HOST
        response = requests.get(
            f"{base.rstrip('/')}/{endpoint}",
            params=params,
            proxies=get_proxies(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def _as_list(self, value: object) -> List[Dict]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            for key in ("data", "results", "activity"):
                nested = value.get(key)
                if isinstance(nested, list):
                    return [item for item in nested if isinstance(item, dict)]
            return [value]
        return []

    def scan_wallet(self, address: str, leaderboard_pnl: float = None) -> Dict:
        if not self._is_valid_address(address):
            return {
                "address": address,
                "valid": False,
                "error": "Invalid EVM wallet address",
                "stats": {},
                "specialization": {},
                "recommendation": "",
            }

        profile = self._fetch("public-profile", {"address": address})
        profile = profile if isinstance(profile, dict) else {}
        profile_wallet = profile.get("proxyWallet") or profile.get("proxy_wallet") or address

        positions = self._as_list(self._fetch("positions", {"user": profile_wallet, "limit": 50}))
        closed_positions = self._as_list(self._fetch("closed-positions", {"user": profile_wallet, "limit": 50}))
        activity = self._as_list(self._fetch("activity", {"user": profile_wallet, "limit": 100}))
        trades = self._as_list(self._fetch("trades", {"user": profile_wallet, "limit": 100}))
        value_payload = self._fetch("value", {"user": profile_wallet})
        value_payload = value_payload if isinstance(value_payload, dict) else {}

        total_volume = sum(float(t.get("cash") or t.get("amount") or t.get("value") or 0) for t in trades)
        if not total_volume:
            total_volume = sum(float(a.get("cash") or a.get("amount") or a.get("value") or 0) for a in activity)

        profit = sum(float(p.get("realizedPnl") or p.get("cashPnl") or p.get("pnl") or 0) for p in closed_positions)
        portfolio_value = float(value_payload.get("value") or 0)
        if not portfolio_value:
            portfolio_value = sum(float(p.get("currentValue") or p.get("value") or 0) for p in positions)

        stats = {
            "total_trades": max(len(trades), len(activity)),
            "win_rate": 0.0,
            "total_volume_usdc": total_volume,
            "portfolio_value": portfolio_value,
            "profit": profit,
            "leaderboard_pnl": leaderboard_pnl,
        }
        specialization = self.analyzer._detect_specialization(stats, trades or activity or positions)

        return {
            "address": address,
            "valid": True,
            "profile": profile,
            "profile_wallet": profile_wallet,
            "stats": stats,
            "specialization": specialization,
            "positions": positions,
            "closed_positions": closed_positions,
            "activity": activity,
            "recent_trades": trades,
            "trades": trades,
            "recommendation": "Wallet Mirror possible: surveiller le sizing, la liquidité et le slippage.",
            "pnl": profit,
        }

    def format_report(self, result: Dict) -> str:
        address = result.get("address", "unknown")
        profile_wallet = result.get("profile_wallet") or address
        base_report = self.formatter.format_report(result)
        links = [
            "",
            "*Liens*",
            f"• Polymarket: https://polymarket.com/profile/{address}",
            f"• Polyanalytics: https://polyanalytics.com/address/{profile_wallet}",
            f"• Polygonscan: https://polygonscan.com/address/{profile_wallet}",
            "",
            "*Adresses*",
            f"• ETH/POL: <code>{address}</code>",
            f"• Proxy Polymarket/Polygon: <code>{profile_wallet}</code>",
        ]
        recommendation = result.get("recommendation")
        if recommendation:
            links.extend(["", f"*Recommendation*: {recommendation}"])
        return base_report + "\n" + "\n".join(links)

__all__ = [
    'Config',
    'WalletScanner',
    'WalletScannerClient',
    'WalletAnalyzer', 
    'WalletScorer',
    'WalletFormatter',
    'requests',
]
