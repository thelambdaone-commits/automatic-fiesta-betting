import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Optional

from core.config import Config


SMART_COPY_FILE = Config.CONFIG_DIR / "targets" / "smart_copy_profiles.json"


@dataclass
class SmartCopyProfile:
    name: str
    wallet: str
    portfolio_amount: float
    wallet_type: str
    assigned_wallet: str = ""
    assigned_wallet_label: str = "auto"
    mode: str = "Percentage"
    trade_size_percent: float = 1.0
    single_trade_limit: float = 10.0
    price_range: str = "No Filter"
    slippage: str = "Any Price"
    auto_tp_sl: bool = False
    simulation: bool = True
    enabled: bool = True
    ai_summary: str = ""


def _to_float(value, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if number >= 0 else default


def infer_wallet_type(scan_result: Optional[Dict]) -> str:
    if not scan_result:
        return "unknown"

    stats = scan_result.get("stats") or {}
    spec = scan_result.get("specialization") or {}
    trades = int(stats.get("total_trades", 0) or 0)
    volume = _to_float(stats.get("total_volume_usdc"))
    portfolio_value = _to_float(stats.get("portfolio_value"))
    win_rate = _to_float(stats.get("win_rate"))
    category = str(spec.get("category") or "unknown")
    confidence = _to_float(spec.get("confidence"))

    if portfolio_value >= 10000 or volume >= 100000:
        return "whale"
    if confidence >= 0.55 and category not in {"unknown", "inconnue"}:
        return f"specialist:{category}"
    if trades >= 50 and win_rate >= 0.55:
        return "active_profitable"
    if trades >= 20:
        return "active"
    return "new_or_low_history"


def build_smart_copy_profile(
    name: str,
    wallet: str,
    portfolio_amount: float,
    scan_result: Optional[Dict] = None,
    assigned_wallet: str = "",
    assigned_wallet_label: str = "auto",
    simulation: bool = True,
) -> SmartCopyProfile:
    portfolio_amount = _to_float(portfolio_amount)
    wallet_type = infer_wallet_type(scan_result)
    stats = (scan_result or {}).get("stats") or {}

    limit = min(10.0, portfolio_amount) if portfolio_amount > 0 else 10.0

    mode_label = "simulé" if simulation else "LIVE"
    summary = (
        f"Profil IA {mode_label}: {wallet_type}. "
        f"Copie 100% du montant leader avec plafond {limit:.2f} USDC. "
        f"Trades publics={int(stats.get('total_trades', 0) or 0)}, "
        f"volume={float(stats.get('total_volume_usdc', 0) or 0):.2f} USDC."
    )

    return SmartCopyProfile(
        name=(name or "Smart Copy").strip(),
        wallet=(wallet or "").strip(),
        portfolio_amount=portfolio_amount,
        wallet_type=wallet_type,
        assigned_wallet=(assigned_wallet or "").strip(),
        assigned_wallet_label=(assigned_wallet_label or "auto").strip(),
        single_trade_limit=round(limit, 2),
        simulation=simulation,
        ai_summary=summary,
    )


def load_profiles(path: Path = SMART_COPY_FILE) -> Dict[str, Dict]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    profiles = data.get("profiles", data)
    return profiles if isinstance(profiles, dict) else {}


def save_profile(profile: SmartCopyProfile, path: Path = SMART_COPY_FILE) -> None:
    profiles = load_profiles(path)
    profiles[profile.wallet.lower()] = asdict(profile)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump({"profiles": profiles}, file, indent=2)


def get_profile(wallet: str, path: Path = SMART_COPY_FILE) -> Optional[Dict]:
    if not wallet:
        return None
    return load_profiles(path).get(wallet.lower())


def apply_profile_to_amount(leader_amount: float, profile: Optional[Dict]) -> float:
    if not profile or not profile.get("enabled", True):
        return leader_amount

    percent = _to_float(profile.get("trade_size_percent"), 1.0)
    limit = _to_float(profile.get("single_trade_limit"), 10.0)
    portfolio = _to_float(profile.get("portfolio_amount"))
    amount = leader_amount * percent
    caps = [limit]
    if portfolio > 0:
        caps.append(portfolio)
    return max(0.0, min(amount, *caps))



def apply_adaptive_profile(wallet: str, leader_amount: float, profile: Optional[Dict]) -> float:
    """Applique le redimensionnement dynamique selon win/loss streak."""
    if not profile or not profile.get("enabled", True):
        return leader_amount
    
    # Lire streak depuis les logs
    from services.jsonl_logger import get_wallet_streak
    streak_data = get_wallet_streak(wallet)
    
    win_streak = streak_data.get("win_streak", 0)
    loss_streak = streak_data.get("loss_streak", 0)
    
    # Limites de base
    amount = apply_profile_to_amount(leader_amount, profile)
    
    # Pas de streak -> pas d'ajustement
    if win_streak == 0 and loss_streak == 0:
        return amount
    
    # Win streak: augmenter jusqu'à +50%
    if win_streak > 0:
        multiplier = min(1.5, 1.0 + (win_streak * 0.1))
        logger.info(f"Adaptive Copy: win_streak={win_streak}, multiplier={multiplier}")
        return amount * multiplier
    
    # Loss streak: réduire jusqu'à -50%
    if loss_streak > 0:
        multiplier = max(0.5, 1.0 - (loss_streak * 0.1))
        logger.info(f"Adaptive Copy: loss_streak={loss_streak}, multiplier={multiplier}")
        return amount * multiplier
    
    return amount


def format_profile(profile: SmartCopyProfile | Dict) -> str:
    data = asdict(profile) if isinstance(profile, SmartCopyProfile) else profile
    tp_sl = "Disabled" if not data.get("auto_tp_sl") else "Enabled"
    assigned = data.get("assigned_wallet") or "auto"
    assigned_label = data.get("assigned_wallet_label") or "auto"
    return "\n".join(
        [
            "*🧠 Smart Copy simulé configuré*",
            "",
            f"Nom: `{data.get('name')}`",
            f"Mon wallet attribué: `{assigned}`",
            f"Type mon wallet: `{assigned_label}`",
            f"Wallet copié: `{data.get('wallet')}`",
            f"Portfolio simulé: `${float(data.get('portfolio_amount', 0) or 0):.2f}`",
            f"Type wallet IA: `{data.get('wallet_type')}`",
            "",
            f"⚙️ Mode: {data.get('mode', 'Percentage')}",
            f"✏️ Trade Size: {float(data.get('trade_size_percent', 1) or 1) * 100:.0f}% of leader's amount",
            f"📈 Single Trade Limit: ${float(data.get('single_trade_limit', 10) or 10):.2f}",
            f"💲 Price Range: {data.get('price_range', 'No Filter')}",
            f"🎯 Slippage: {data.get('slippage', 'Any Price')}",
            f"🛡️ Auto TP/SL: {tp_sl}",
            "",
            str(data.get("ai_summary") or ""),
        ]
    )


def format_profiles_dashboard(profiles: Dict[str, Dict]) -> str:
    if not profiles:
        return (
            "*🧪 Simulation IA*\n\n"
            "Aucun profil Smart Copy simulé configuré.\n\n"
            "Commande:\n"
            "`/smartcopy <nom> <wallet_cible> <portfolio_usdc> [mon_wallet]`"
        )

    lines = [
        "*🧪 Simulation IA Wallet Mirror*",
        "",
        f"Profils actifs: `{len(profiles)}`",
        "Exécution: `SIMULATION` pour tous les profils Smart Copy",
        "",
    ]
    for index, profile in enumerate(profiles.values(), 1):
        assigned = profile.get("assigned_wallet") or "auto"
        target = profile.get("wallet") or "n/a"
        lines.extend(
            [
                f"*{index}. {profile.get('name') or 'Smart Copy'}*",
                f"  Mon wallet: `{assigned}`",
                f"  Cible copiée: `{target}`",
                f"  Portfolio simulé: `${float(profile.get('portfolio_amount', 0) or 0):.2f}`",
                f"  Plafond/trade: `${float(profile.get('single_trade_limit', 10) or 10):.2f}`",
                f"  Type cible IA: `{profile.get('wallet_type') or 'unknown'}`",
                "  Règles: `100% leader`, `No Filter`, `Any Price`, `TP/SL off`",
                "",
            ]
        )
    lines.append("Ajouter/modifier: `/smartcopy <nom> <wallet_cible> <portfolio_usdc> [mon_wallet]`")
    return "\n".join(lines)
