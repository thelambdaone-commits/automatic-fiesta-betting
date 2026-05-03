from core.config import Config


def start_menu(capital: float = 0.0, pnl: float = 0.0, strategies_count: int = 0) -> str:
    """Start menu text."""
    return "\n".join([
        "🎮 *Polymarket Copy Betting Bot*",
        "",
        f"Capital : `${capital:.2f}` USDC",
        f"PnL : `${pnl:.2f}`",
        f"Stratégies : `{strategies_count}`",
        "",
        "*Menu Principal*",
        "Choisis une option ci-dessous.",
    ])


def copy_trading_menu() -> str:
    """Copy trading menu text."""
    live_enabled = not Config.SIMULATION_MODE and Config.LIVE_TRADING
    mode_emoji = "🔴" if live_enabled else "🧪"
    mode_label = "RÉEL" if live_enabled else "Simulation"
    
    return "\n".join([
        "🔗 *Copy Betting*",
        "",
        f"Mode : {mode_emoji} *{mode_label}*",
        "",
        "*Actions disponibles*",
        "• Voir tes stratégies",
        "• Ajouter une nouvelle stratégie", 
        "• Gérer le Smart Copy IA",
        "• Configurer l'AutoPilot",
        "",
        "Toutes les options sont ci-dessous.",
    ])


def discover_menu() -> str:
    """Discover menu text."""
    return "\n".join([
        "🧭 *Découvrir*",
        "",
        "*Explorer et trouver*",
        "• Scanner un wallet pour l'analyser",
        "• Voir les top wallets",
        "• Suivre l'activité des baleines",
        "• Rechercher des marchés",
        "• Analyser avec l'IA",
        "",
        "Choisis une option dans le menu.",
    ])


def settings_menu() -> str:
    """Settings menu text."""
    mode = "RÉEL" if (not Config.SIMULATION_MODE and Config.LIVE_TRADING) else "Simulation"
    max_trade = float(getattr(Config, 'MAX_ORDER_SIZE', 1000))
    slippage = float(getattr(Config, 'SLIPPAGE_TOLERANCE', 0.01)) * 100
    
    return "\n".join([
        "⚙️ *Paramètres du Bot*",
        "",
        f"Mode actuel: *{mode}*",
        f"Max/pari: `${max_trade:.2f}`",
        f"Slippage: `{slippage:.1f}%`",
        "",
        "Utilise les boutons ci-dessous pour modifier les réglages.",
    ])
