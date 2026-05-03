import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import requests
import websockets

ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from settings import Config


def _ok(name, detail):
    return {"name": name, "ok": True, "detail": detail}


def _fail(name, detail):
    return {"name": name, "ok": False, "detail": detail}


def _redact(value):
    if not value:
        return "<empty>"
    if len(value) <= 8:
        return "<set>"
    return f"{value[:4]}...{value[-4:]}"


def check_config():
    required = {
        "POLYMARKET_PRIVATE_KEY": Config.PRIVATE_KEY,
        "POLYMARKET_API_KEY": Config.API_KEY,
        "POLYMARKET_SECRET": Config.SECRET,
        "POLYMARKET_PASSPHRASE": Config.PASSPHRASE,
        "POLYGONSCAN_API_KEY": Config.POLYGONSCAN_API_KEY,
        "RPC_URL": Config.RPC_URL,
        "WS_URL": Config.WS_URL,
        "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
        "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID"),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        return _fail("config", "Missing: " + ", ".join(missing))

    target_count = len(Config.TARGET_WALLETS)
    target_detail = f"target_wallets={target_count}, test_wallet={'yes' if Config.TEST_WALLET else 'no'}"
    return _ok("config", target_detail)


def check_telegram(timeout=10):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return _fail("telegram", "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing")

    try:
        response = requests.get(
            f"https://api.telegram.org/bot{token}/getMe",
            timeout=timeout,
        )
        data = response.json()
    except Exception as exc:
        return _fail("telegram", f"{type(exc).__name__}: {exc}")

    if not data.get("ok"):
        return _fail("telegram", str(data.get("description") or data))

    username = data.get("result", {}).get("username", "<unknown>")
    return _ok("telegram", f"bot=@{username}, chat_id={_redact(chat_id)}")


def check_rpc(timeout=10):
    if not Config.RPC_URL:
        return _fail("rpc", "RPC_URL missing")

    payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []}
    try:
        response = requests.post(Config.RPC_URL, json=payload, timeout=timeout)
        data = response.json()
    except Exception as exc:
        return _fail("rpc", f"{type(exc).__name__}: {exc}")

    block_hex = data.get("result")
    if not block_hex:
        return _fail("rpc", str(data.get("error") or data))

    return _ok("rpc", f"block={int(block_hex, 16)}")


async def _check_ws_async(timeout=10):
    if not Config.WS_URL:
        return _fail("websocket", "WS_URL missing")

    payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []}
    try:
        async with websockets.connect(Config.WS_URL, open_timeout=timeout) as websocket:
            await websocket.send(json.dumps(payload))
            raw = await asyncio.wait_for(websocket.recv(), timeout=timeout)
            data = json.loads(raw)
    except Exception as exc:
        return _fail("websocket", f"{type(exc).__name__}: {exc}")

    block_hex = data.get("result")
    if not block_hex:
        return _fail("websocket", str(data.get("error") or data))

    return _ok("websocket", f"block={int(block_hex, 16)}")


def check_ws(timeout=10):
    return asyncio.run(_check_ws_async(timeout=timeout))


def check_polygonscan(timeout=10):
    api_key = Config.POLYGONSCAN_API_KEY
    if not api_key:
        return _fail("polygonscan", "POLYGONSCAN_API_KEY missing")

    params = {
        "chainid": "137",
        "module": "stats",
        "action": "maticprice",
        "apikey": api_key,
    }
    try:
        response = requests.get("https://api.etherscan.io/v2/api", params=params, timeout=timeout)
        data = response.json()
    except Exception as exc:
        return _fail("polygonscan", f"{type(exc).__name__}: {exc}")

    if data.get("status") != "1":
        return _fail("polygonscan", str(data.get("result") or data.get("message") or data))

    result = data.get("result") or {}
    price = result.get("maticusd") or result.get("ethusd") or "ok"
    return _ok("polygonscan", f"Polygon API V2 ok, price={price}")


def check_groq(timeout=20):
    try:
        from services.groq_advisor import GroqAdvisor

        advisor = GroqAdvisor()
        result = advisor.healthcheck(timeout=timeout)
    except Exception as exc:
        return _fail("groq", f"{type(exc).__name__}: {exc}")

    if "groq-ok" not in result.lower():
        return _fail("groq", f"unexpected response: {result[:120]}")
    return _ok("groq", f"model={Config.GROQ_MODEL}")


CHECKS = {
    "config": check_config,
    "telegram": check_telegram,
    "rpc": check_rpc,
    "ws": check_ws,
    "polygonscan": check_polygonscan,
    "groq": check_groq,
}


def run_checks(names):
    results = []
    for name in names:
        check = CHECKS[name]
        results.append(check())
    return results


def format_results(results):
    lines = []
    for result in results:
        marker = "OK" if result["ok"] else "FAIL"
        lines.append(f"{marker} {result['name']}: {result['detail']}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Validate Polymarket bot runtime setup.")
    parser.add_argument(
        "checks",
        nargs="*",
        choices=sorted(CHECKS),
        default=list(CHECKS),
        help="Checks to run. Defaults to all checks.",
    )
    args = parser.parse_args()

    results = run_checks(args.checks)
    print(format_results(results))
    return 0 if all(result["ok"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
