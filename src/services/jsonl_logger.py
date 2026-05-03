"""
JSONL Logger for Polymarket Copy Trading Bot.
"""
import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)


def _jsonl_path(name: str) -> str:
    return os.path.join(DATA_DIR, name + ".jsonl")


def append_record(name: str, record: Dict):
    record["_ts"] = time.time()
    record["_iso"] = datetime.now(timezone.utc).isoformat()
    path = _jsonl_path(name)
    with open(path, mode="a", encoding="utf-8") as f:
        line = json.dumps(record, ensure_ascii=False)
        f.write(line + "\n")


def read_records(name: str, limit: Optional[int] = None) -> List[Dict]:
    path = _jsonl_path(name)
    if not os.path.exists(path):
        return []
    records = []
    with open(path, mode="r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if limit is not None and limit > 0:
        records = records[-limit:]
    return records


def log_trade(wallet: str, market: str, token_id: str, side: str,
              size: float, price: float, slippage: float, success: bool,
              pnl: float = 0.0):
    append_record("trades", {
        "wallet": wallet,
        "market": market,
        "token_id": token_id,
        "side": side,
        "size": size,
        "price": price,
        "slippage": slippage,
        "success": success,
        "pnl": pnl,
    })


def cache_wallets(wallets: List[Dict]):
    path = _jsonl_path("wallets")
    with open(path, mode="w", encoding="utf-8") as f:
        now = time.time()
        iso = datetime.now(timezone.utc).isoformat()
        for index, w in enumerate(wallets, 1):
            wallet = w.get("wallet") or w.get("proxyWallet") or w.get("address")
            record = {
                "rank": int(w.get("rank") or index),
                "wallet": wallet,
                "address": wallet,
                "proxyWallet": w.get("proxyWallet") or wallet,
                "username": w.get("username") or w.get("userName"),
                "pnl": w.get("pnl", 0),
                "volume": w.get("volume", w.get("vol", 0)),
                "source": w.get("source", "Leaderboard API"),
                "_ts": now,
                "_iso": iso,
            }
            line = json.dumps(record, ensure_ascii=False)
            f.write(line + "\n")


def get_cached_wallets(max_age_seconds: int = 3600) -> List[Dict]:
    records = read_records("wallets")
    if not records:
        return []
    newest_ts = max(r.get("_ts", 0) for r in records)
    if time.time() - newest_ts > max_age_seconds:
        return []
    return records


def log_signal(signal_type: str, details: Dict, result: str = "pending"):
    append_record("signals", {
        "signal_type": signal_type,
        **details,
        "result": result,
    })


def log_ai_training_data(wallet: str, pnl: float, winrate: float, copied: bool, result: str):
    append_record("ai_dataset", {
        "wallet": wallet,
        "pnl": pnl,
        "winrate": winrate,
        "copied": copied,
        "result": result,
    })

def get_wallet_streak(wallet: str, limit: int = 50) -> Dict:
    """
    Calcule la streak win/loss pour un wallet.
    Retourne: {"win_streak": int, "loss_streak": int, "last_10_pnl": float}
    """
    trades = read_records("trades")
    
    # Filtrer par wallet
    wallet_trades = [t for t in trades if t.get("wallet") == wallet][-limit:]
    
    if not wallet_trades:
        return {"win_streak": 0, "loss_streak": 0, "last_10_pnl": 0.0}
    
    # Calculer P&L cumulé last 10
    last_10 = wallet_trades[-10:]
    last_10_pnl = sum(float(t.get("pnl", 0) or 0) for t in last_10)
    
    # Calculer streaks
    win_streak = 0
    loss_streak = 0
    
    # Parcourir du plus récent au plus ancien
    for trade in reversed(wallet_trades):
        pnl = float(trade.get("pnl", 0) or 0)
        if pnl > 0:
            if loss_streak > 0:
                break
            win_streak += 1
        elif pnl < 0:
            if win_streak > 0:
                break
            loss_streak += 1
        else:
            break
    
    return {
        "win_streak": win_streak,
        "loss_streak": loss_streak,
        "last_10_pnl": last_10_pnl
    }
def get_wallets_performance() -> Dict[str, Dict]:
    """
    Aggregate performance metrics for each followed wallet.
    Returns: {wallet_address: {pnl, volume, trades, success_rate, is_profitable}}
    """
    trades = read_records("trades")
    perf = {}
    
    for t in trades:
        w = t.get("wallet", "unknown").lower()
        if w not in perf:
            perf[w] = {"pnl": 0.0, "volume": 0.0, "trades": 0, "success": 0}
            
        pnl = float(t.get("pnl", 0) or 0)
        size = float(t.get("size", 0) or 0)
        success = 1 if t.get("success") or pnl > 0 else 0
        
        perf[w]["pnl"] += pnl
        perf[w]["volume"] += size
        perf[w]["trades"] += 1
        perf[w]["success"] += success
        
    # Calculate derived stats
    for w in perf:
        p = perf[w]
        p["success_rate"] = (p["success"] / p["trades"] * 100) if p["trades"] > 0 else 0
        p["is_profitable"] = p["pnl"] > 0
        p["score"] = (p["pnl"] * 0.7) + (p["success_rate"] * 0.3) # Simple ranking score
        
    return perf
