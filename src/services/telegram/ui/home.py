from core.config import Config


def home_text() -> str:
    live_enabled = not Config.SIMULATION_MODE and Config.LIVE_TRADING
    mode_emoji = "🔴" if live_enabled else "🧪"
    mode_label = "RÉEL" if live_enabled else "Simulation"
    copy_status = "actif" if Config.TARGET_WALLETS else "à configurer"
    targets_count = len(Config.TARGET_WALLETS or [])

    return "\n".join(
        [
            "🎮 *Polymarket Copy Betting Bot*",
            "",
            f"Mode : {mode_emoji} *{mode_label}*",
            f"Copy trading : *{copy_status}*",
            f"Wallets suivis : `{targets_count}`",
            "",
            "*Tableau de bord*",
            "• Copier un wallet, créer un Smart Copy IA ou voir les paires.",
            "• Scanner un wallet, chercher des marchés et consulter les meilleurs wallets.",
            "• Vérifier ton wallet, les risques, le statut et les réglages.",
            "",
            "Toutes les actions principales sont disponibles ci-dessous."
        ]
    )
