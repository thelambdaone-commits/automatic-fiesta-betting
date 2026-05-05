import re
from typing import Any, Dict, Iterable, Optional

import requests

from core.config import Config


WALLET_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
ANY_WALLET_RE = re.compile(r"0x[a-fA-F0-9]{40}")
PROXY_WALLET_RE = re.compile(r'"proxyWallet"\s*:\s*"(0x[a-fA-F0-9]{40})"', re.IGNORECASE)


class PolymarketProfileResolutionError(ValueError):
    """Raised when a Polymarket profile handle cannot be resolved."""


def is_wallet_address(value: str) -> bool:
    return bool(WALLET_RE.fullmatch((value or "").strip()))


def normalize_profile_input(value: str) -> str:
    """Extract a wallet or Polymarket handle from command input."""
    value = (value or "").strip().rstrip("/")
    if not value:
        return ""

    if is_wallet_address(value):
        return value

    match = re.search(r"polymarket\.com/(?:[a-z]{2}(?:-[a-z]+)?/)?(?:profile/)?(@?[^/?#]+)", value, re.IGNORECASE)
    if match:
        value = match.group(1)

    if value.startswith("@"):
        value = value[1:]

    return value.strip()


def _iter_profiles(payload: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
        return

    if not isinstance(payload, dict):
        return

    for key in ("profiles", "users", "data", "results"):
        items = payload.get(key)
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    yield item

    if any(key in payload for key in ("proxyWallet", "proxy_wallet", "address", "username", "name")):
        yield payload


def _profile_wallet(profile: Dict[str, Any]) -> str:
    for key in ("proxyWallet", "proxy_wallet", "wallet", "address"):
        value = str(profile.get(key) or "").strip()
        if is_wallet_address(value):
            return value
    return ""


def _profile_matches(profile: Dict[str, Any], handle: str) -> bool:
    expected = handle.lower().lstrip("@")
    for key in ("username", "name", "pseudonym", "displayUsername"):
        value = str(profile.get(key) or "").strip().lower().lstrip("@")
        if value == expected:
            return True
    return False


def _fetch_json(url: str, params: Dict[str, Any], timeout: int) -> Any:
    response = requests.get(url, params=params, timeout=timeout)
    if not response.ok:
        return None
    return response.json()


def _resolve_from_apis(handle: str, timeout: int) -> str:
    gamma_host = Config.GAMMA_API_HOST.rstrip("/")
    data_host = Config.DATA_API_HOST.rstrip("/")
    queries = [
        (f"{gamma_host}/public-search", {"q": handle, "limit": 10}),
        (f"{gamma_host}/search", {"query": handle, "type": "profiles", "limit": 10}),
        (f"{gamma_host}/profiles", {"username": handle}),
        (f"{data_host}/profiles", {"username": handle}),
    ]

    fallback_wallet = ""
    for url, params in queries:
        try:
            payload = _fetch_json(url, params=params, timeout=timeout)
        except Exception:
            continue

        for profile in _iter_profiles(payload):
            wallet = _profile_wallet(profile)
            if not wallet:
                continue
            if _profile_matches(profile, handle):
                return wallet
            fallback_wallet = fallback_wallet or wallet

    return fallback_wallet


def _resolve_from_profile_page(handle: str, timeout: int) -> str:
    url = f"https://polymarket.com/@{handle}"
    response = requests.get(url, timeout=timeout)
    if not response.ok:
        return ""

    text = response.text or ""
    match = PROXY_WALLET_RE.search(text)
    if match:
        return match.group(1)

    # Last resort: the profile page can include repeated position payloads.
    wallets = ANY_WALLET_RE.findall(text)
    return wallets[0] if len(set(wallets)) == 1 else ""


def resolve_polymarket_profile(value: str, timeout: Optional[int] = None) -> str:
    """Resolve a wallet address, @handle, or Polymarket profile URL to a proxy wallet."""
    normalized = normalize_profile_input(value)
    if not normalized:
        raise PolymarketProfileResolutionError("profil ou wallet vide")
    if is_wallet_address(normalized):
        return normalized

    timeout = int(timeout or getattr(Config, "REQUEST_TIMEOUT", 10) or 10)
    wallet = _resolve_from_apis(normalized, timeout=timeout)
    if wallet:
        return wallet

    wallet = _resolve_from_profile_page(normalized, timeout=timeout)
    if wallet:
        return wallet

    raise PolymarketProfileResolutionError(f"profil Polymarket introuvable: @{normalized}")
