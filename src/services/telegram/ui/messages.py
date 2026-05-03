from core.config import Config


def balance_text(balance_info: dict) -> str:
    """Format balance information."""
    if not balance_info:
        return "❌ Impossible de récupérer le solde USDC."
    
    balance = float(balance_info.get('balance', 0))
    return "\n".join([
        "💰 *Solde USDC*",
        "",
        f"Disponible: `${balance:.2f}` USDC",
        f"Wallet: `{balance_info.get('address', 'N/A')}`",
        "",
        "Utilise `/mirror <wallet>` pour copier un wallet.",
    ])


def error_text(error_msg: str) -> str:
    """Format error message."""
    return "\n".join([
        "❌ *Erreur*",
        "",
        f"`{error_msg}`",
        "",
        "Vérifie les logs pour plus de détails.",
    ])


def success_text(action: str, details: str = "") -> str:
    """Format success message."""
    return "\n".join([
        "✅ *Succès*",
        "",
        f"Action: {action}",
        f"Détails: {details}" if details else "",
        "",
        "Utilise le menu pour continuer.",
    ])


def wallet_analysis_text(scan_result: dict) -> tuple:
    """Format wallet analysis result with keyboard."""
    if not scan_result:
        return "❌ Analyse impossible. Vérifie l'adresse du wallet.", None
    
    address = scan_result.get("address", "")
    short = f"{address[:6]}...{address[-3:]}" if len(address) >= 12 else address
    stats = scan_result.get("stats", {})
    total_trades = stats.get('total_trades', 0)
    volume = float(stats.get('total_volume_usdc', 0)) or 0
    win_rate = float(stats.get('win_rate', 0)) or 0
    pnl = float(stats.get('leaderboard_pnl') or 0) or 0
    
    # Get profile info
    profile = scan_result.get("profile", {})
    username = profile.get("pseudonym") or profile.get("name") or "Inconnu"
    x_username = profile.get("xUsername", "")
    
    lines = [
        "📊 *Analyse du Wallet*",
        "",
        f"👤 Pseudo: {username}",
        f"🔗 Adresse: `{short}`",
    ]
    
    if x_username:
        lines.append(f"🐦 Twitter: @{x_username}")
    
    lines.append("")
    
    # If no trading data available
    if total_trades == 0:
        lines.extend([
            "⚠️ *Aucune donnée de trading trouvée*",
            "",
            "L'API Polymarket ne fournit pas les statistiques de trading",
            "pour ce wallet via les endpoints publics.",
            "",
            "💡 _Le wallet peut être valide mais ne pas avoir_",
            "_de données publiques via l'API actuelle._",
        ])
    else:
        lines.extend([
            f"📈 Trades total: `{total_trades}`",
            f"💰 Volume: `${volume:.2f}`",
            f"🎯 Win rate: `{win_rate:.1%}`",
        ])
        if pnl != 0:
            lines.append(f"📊 PnL: `${pnl:.2f}`")
    
    lines.append("")
    lines.append(f"🔍 [Voir sur Polymarket](https://polymarket.com/profile/{address})")
    
    # Create keyboard with action buttons
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📜 Historique", "callback_data": f"trades_{address}"},
                {"text": "📋 Ordres", "callback_data": f"orders_{address}"},
                {"text": "💼 Positions", "callback_data": f"positions_{address}"},
            ],
            [
                {"text": "🧠 Analyse IA", "callback_data": f"groq_{address}"},
            ],
            [
                {"text": "🔙 Retour", "callback_data": "menu:decouvrir"},
            ],
        ]
    }
    
    return "\n".join(lines), keyboard
