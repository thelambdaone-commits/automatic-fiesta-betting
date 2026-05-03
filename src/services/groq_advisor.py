import json
from typing import List, Optional

import requests

from core.config import Config
from services.wallet_ranker import WalletRanker, WalletScore


class GroqAdvisor:
    endpoint = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or Config.GROQ_API_KEY
        self.model = model or Config.GROQ_MODEL
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is required")

    def healthcheck(self, timeout: int = 20) -> str:
        content = self.complete(
            "Reply with exactly: groq-ok",
            system="You are a concise healthcheck.",
            timeout=timeout,
            max_tokens=16,
        )
        return content.strip()

    def analyze_wallets(self, scores: List[WalletScore], timeout: int = 45) -> str:
        wallet_data = WalletRanker.to_prompt(scores)
        return self.complete(
            (
                "Analyze these Polymarket wallet backtest results and recommend which wallets "
                "to copytrade, which to avoid, and conservative sizing rules. "
                "Use only the provided data. Mention uncertainty and data gaps. "
                f"Wallet data: {wallet_data}"
            ),
            system=(
                "You are a risk-aware copytrading analyst. You never guarantee profit. "
                "You prefer conservative sizing, liquidity checks, and avoiding wallets "
                "with too few trades or unclear PnL quality."
            ),
            timeout=timeout,
            max_tokens=600,
        )

    def analyze_wallets_from_data(self, wallet_data: list, timeout: int = 45) -> str:
        """
        Analyze raw wallet data (from Polymarket Analytics) and recommend which to copytrade.
        
        Args:
            wallet_data: List of dicts with keys: wallet, pnl, win_rate, volume, etc.
            timeout: Request timeout in seconds
        """
        # Format data for the prompt
        formatted_data = []
        for item in wallet_data:
            formatted_data.append(
                f"Wallet: {item['wallet']}, PnL: {item.get('pnl', 0):.2f}, "
                f"Win Rate: {item.get('win_rate', 0):.1%}, "
                f"Volume: {item.get('volume', 0):.2f}"
            )
        
        data_str = "\n".join(formatted_data)
        
        return self.complete(
            (
                "Analyze these Polymarket wallet performance data and recommend which wallets "
                "to copytrade, which to avoid, and conservative sizing rules. "
                "Consider PnL, win rate, and trading volume. "
                "Use only the provided data. Mention uncertainty and data gaps.\n\n"
                f"Wallet data:\n{data_str}"
            ),
            system=(
                "You are a risk-aware copytrading analyst. You never guarantee profit. "
                "You prefer conservative sizing, liquidity checks, and avoiding wallets "
                "with too few trades or unclear PnL quality."
            ),
            timeout=timeout,
            max_tokens=600,
        )

    def complete(self, user: str, system: str, timeout: int = 45, max_tokens: int = 400) -> str:
        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
                "max_tokens": max_tokens,
            },
            timeout=timeout,
        )
        try:
            data = response.json()
        except json.JSONDecodeError:
            response.raise_for_status()
            raise

        if response.status_code >= 400:
            raise RuntimeError(data.get("error", {}).get("message") or str(data))

        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("Groq returned no choices")
        return choices[0]["message"]["content"]
