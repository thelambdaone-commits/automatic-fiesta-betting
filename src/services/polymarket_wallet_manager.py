import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import requests
from eth_account import Account

from _py_clob_client.client import ClobClient
from core.config import Config


WALLETS_FILE = Config.CONFIG_DIR / "wallets" / "polymarket_wallets.json"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
COPY_TRADE_ENTRYPOINT = PROJECT_ROOT / "src" / "main_copy_trade.py"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def short_address(address: str) -> str:
    address = str(address or "")
    return f"{address[:6]}...{address[-4:]}" if len(address) >= 12 else address or "n/a"


def signer_address_from_key(private_key: Optional[str] = None) -> str:
    key = private_key or Config.PRIVATE_KEY
    return Account.from_key(key).address if key else ""


def load_wallet_records() -> Dict:
    if not WALLETS_FILE.exists():
        return {"wallets": [], "active_wallet_id": None}
    with WALLETS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)
    data.setdefault("wallets", [])
    data.setdefault("active_wallet_id", None)
    return data


def save_wallet_records(data: Dict):
    WALLETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with WALLETS_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def detect_proxy_wallet(signer_address: str, timeout: Optional[int] = None) -> Dict:
    timeout = int(timeout or getattr(Config, "REQUEST_TIMEOUT", 10) or 10)
    try:
        response = requests.get(
            f"{Config.GAMMA_API_HOST.rstrip('/')}/public-profile",
            params={"address": signer_address},
            timeout=timeout,
        )
        if response.ok:
            profile = response.json()
            if isinstance(profile, dict):
                proxy_wallet = profile.get("proxyWallet") or profile.get("proxy_wallet") or ""
                if proxy_wallet:
                    return {"proxy_wallet": proxy_wallet, "proxy_status": "detected", "profile": profile}
    except Exception as exc:
        return {"proxy_wallet": "", "proxy_status": f"unavailable: {exc}", "profile": {}}

    return {"proxy_wallet": "", "proxy_status": "not_detected", "profile": {}}


def derive_clob_credentials(private_key: str) -> Dict:
    client = ClobClient(
        Config.HOST,
        key=private_key,
        chain_id=Config.CHAIN_ID,
    )
    creds = client.create_or_derive_api_creds()
    if not creds or not creds.api_key or not creds.api_secret or not creds.api_passphrase:
        raise RuntimeError("credentials CLOB incomplets")
    return {
        "polymarket_api_key": creds.api_key,
        "polymarket_api_secret": creds.api_secret,
        "polymarket_api_passphrase": creds.api_passphrase,
    }


def backup_session_file() -> Optional[Path]:
    if not Config.SESSION_FILE.exists():
        return None
    backup_dir = Config.SESSION_FILE.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_dir / f"default.{stamp}.json"
    shutil.copy2(Config.SESSION_FILE, backup_path)
    return backup_path


def update_active_session(private_key: str, api_creds: Dict) -> Optional[Path]:
    data = {}
    if Config.SESSION_FILE.exists():
        with Config.SESSION_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

    backup_path = backup_session_file()
    data.update(api_creds)
    data["private_key"] = private_key
    data.setdefault("host", Config.HOST)
    data.setdefault("chain_id", Config.CHAIN_ID)
    data["updated_at"] = utc_now()

    Config.SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    with Config.SESSION_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    Config.PRIVATE_KEY = private_key
    Config.API_KEY = api_creds["polymarket_api_key"]
    Config.SECRET = api_creds["polymarket_api_secret"]
    Config.PASSPHRASE = api_creds["polymarket_api_passphrase"]

    return backup_path


def create_and_activate_wallet(label: str = "Polymarket Wallet") -> Dict:
    account = Account.create()
    private_key = account.key.hex()
    if not private_key.startswith("0x"):
        private_key = "0x" + private_key
    signer_address = account.address

    api_creds = derive_clob_credentials(private_key)
    backup_path = update_active_session(private_key, api_creds)
    proxy_info = detect_proxy_wallet(signer_address)
    proxy_wallet = proxy_info.get("proxy_wallet") or signer_address
    proxy_status = proxy_info.get("proxy_status") or "not_detected"

    records = load_wallet_records()
    wallet_id = f"pm-{int(datetime.now(timezone.utc).timestamp())}-{signer_address[-6:].lower()}"
    wallet_record = {
        "id": wallet_id,
        "label": label,
        "signer_address": signer_address,
        "proxy_wallet": proxy_wallet,
        "proxy_status": proxy_status,
        "signature_type": 0 if proxy_wallet.lower() == signer_address.lower() else 2,
        "chain_id": Config.CHAIN_ID,
        "created_at": utc_now(),
        "activated_at": utc_now(),
    }
    records["wallets"].append(wallet_record)
    records["active_wallet_id"] = wallet_id
    save_wallet_records(records)

    return {
        **wallet_record,
        "private_key": private_key,
        "api_key": api_creds["polymarket_api_key"],
        "backup_path": str(backup_path) if backup_path else "",
    }


def restart_copy_trade_process() -> Dict:
    """Restart the long-running copy-trade process so it reloads the active session."""
    try:
        subprocess.run(["pkill", "-f", "main_copy_trade.py"], check=False)
        time.sleep(1)
    except Exception as exc:
        return {"ok": False, "pid": None, "error": f"stop failed: {exc}"}

    Config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    output_path = Config.LOG_DIR / "copy_trade_runtime.out"
    env = os.environ.copy()
    src_path = str(PROJECT_ROOT / "src")
    env["PYTHONPATH"] = f"{src_path}:{env.get('PYTHONPATH', '')}".rstrip(":")

    output = output_path.open("ab")
    try:
        process = subprocess.Popen(
            [sys.executable or "python3", str(COPY_TRADE_ENTRYPOINT)],
            cwd=str(PROJECT_ROOT),
            stdout=output,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
            env=env,
        )
    except Exception as exc:
        return {"ok": False, "pid": None, "error": f"start failed: {exc}", "log_path": str(output_path)}
    finally:
        output.close()

    return {
        "ok": True,
        "pid": process.pid,
        "log_path": str(output_path),
    }


def active_wallet_summary() -> Dict:
    signer = signer_address_from_key()
    proxy_info = detect_proxy_wallet(signer) if signer else {"proxy_wallet": "", "proxy_status": "missing"}
    proxy_wallet = proxy_info.get("proxy_wallet") or signer
    return {
        "signer_address": signer,
        "proxy_wallet": proxy_wallet,
        "proxy_status": proxy_info.get("proxy_status") or "not_detected",
    }
