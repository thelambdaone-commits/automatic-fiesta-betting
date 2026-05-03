from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from settings import Config


def prompt_value(label, default=""):
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def prompt_float(label, default):
    return float(prompt_value(label, str(default)))


def prompt_int(label, default):
    return int(prompt_value(label, str(default)))


def create_default_session():
    session = {
        "polymarket_api_key": prompt_value("Polymarket API key"),
        "polymarket_api_secret": prompt_value("Polymarket API secret"),
        "polymarket_api_passphrase": prompt_value("Polymarket API passphrase"),
        "private_key": prompt_value("Polymarket private key"),
        "host": prompt_value("Polymarket host", "https://clob.polymarket.com"),
        "chain_id": prompt_int("Chain ID", 137),
        "rpc_url": prompt_value("RPC URL", "https://polygon-rpc.com"),
        "alchemy_ws_url": prompt_value("WebSocket URL", "wss://polygon-rpc.com"),
        "min_order_size": prompt_float("Min order size", 10),
        "max_order_size": prompt_float("Max order size", 1000),
        "slippage_tolerance": prompt_float("Slippage tolerance", 0.01),
        "follow_delay": prompt_float("Follow delay", 1),
        "test_min_order": prompt_float("Test min order", 10),
        "test_max_order": prompt_float("Test max order", 1000),
        "test_slippage": prompt_float("Test slippage", 0.01),
        "test_delay": prompt_float("Test delay", 1),
        "prod_min_order": prompt_float("Prod min order", 100),
        "prod_max_order": prompt_float("Prod max order", 10000),
        "prod_slippage": prompt_float("Prod slippage", 0.005),
        "prod_delay": prompt_float("Prod delay", 2),
        "search_hours": prompt_int("Search hours", 5),
        "match_orders_signature": prompt_value("Match orders signature", "d2539b37"),
    }

    session_path = Config.SESSION_FILE
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(json.dumps(session, indent=2) + "\n", encoding="utf-8")
    print(f"Session créée: {session_path}")


if __name__ == "__main__":
    create_default_session()
