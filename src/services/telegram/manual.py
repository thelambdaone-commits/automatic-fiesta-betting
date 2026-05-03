from .base import *


class TelegramManualMixin:
    def _manual_trade_text(self) -> str:
        mode = "SIMULATION" if Config.SIMULATION_MODE or not Config.LIVE_TRADING else "RÉEL disponible"
        return (
            "*🎯 Pari manuel*\n\n"
            f"Mode actuel: `{mode}`\n\n"
            "Commandes:\n"
            "• Simulation : `/bet BUY <token_id> <montant_usdc>`\n"
            "• Réel confirmé : `/bet confirm BUY <token_id> <montant_usdc>`\n"
            "• Vente : `/bet SELL <token_id> <montant>`\n\n"
            "Sécurité: sans `confirm`, aucun ordre live n'est envoyé."
        )

    def _manual_trade_prompt(self, side: str) -> str:
        side = side.upper()
        return (
            f"*🎯 Pari manuel — {side}*\n\n"
            "Colle le token id Polymarket et le montant.\n\n"
            f"Simulation:\n`/bet {side} <token_id> <montant_usdc>`\n\n"
            f"Réel confirmé :\n`/bet confirm {side} <token_id> <montant_usdc>`\n\n"
            "Utilise d'abord 🔍 Chercher marché si tu n'as pas encore le token id."
        )

    def _execute_manual_bet(self, text: str) -> str:
        parts = text.split()
        if len(parts) not in {4, 5}:
            return (
                "Usage:\n"
                "`/bet BUY <token_id> <montant_usdc>`\n"
                "`/bet confirm BUY <token_id> <montant_usdc>`"
            )

        live_confirmed = len(parts) == 5 and parts[1].lower() == "confirm"
        offset = 2 if live_confirmed else 1
        side = parts[offset].upper()
        token_id = parts[offset + 1].strip()
        try:
            amount = float(parts[offset + 2])
        except ValueError:
            return "Montant invalide. Exemple : `/bet BUY <token_id> 25`"

        if side not in {"BUY", "SELL"}:
            return "Action invalide. Utilise `BUY` ou `SELL`."
        if amount <= 0:
            return "Montant invalide. Le montant doit être positif."

        max_order = Config.PROD_MAX_ORDER if live_confirmed else Config.TEST_MAX_ORDER
        min_order = Config.PROD_MIN_ORDER if live_confirmed else Config.TEST_MIN_ORDER
        if amount < min_order or amount > max_order:
            return f"Montant hors limites: `{min_order}` à `{max_order}` USDC."

        if not live_confirmed or Config.SIMULATION_MODE or not Config.LIVE_TRADING:
            return (
                "*🧪 Pari manuel simulé*\n\n"
                f"Side: `{side}`\n"
                f"Token: `{token_id}`\n"
                f"Montant: `{amount:.2f} USDC`\n\n"
                "Aucun ordre live envoyé.\n"
                "Pour envoyer en live: `/bet confirm "
                f"{side} {token_id} {amount:.2f}`"
            )

        try:
            import asyncio
            from services.copy_trade import PolymarketTrader

            trader = PolymarketTrader(mode="prod")
            try:
                response = asyncio.run(trader.place_order(token_id=token_id, direction=side, amount=amount))
            finally:
                asyncio.run(trader.close())
            return (
                "*✅ Pari manuel envoyé*\n\n"
                f"Side: `{side}`\n"
                f"Token: `{token_id}`\n"
                f"Montant: `{amount:.2f} USDC`\n"
                f"Réponse: `{str(response)[:800]}`"
            )
        except Exception as e:
            logger.exception("Manual bet failed")
            return f"Erreur pari manuel: `{e}`"
