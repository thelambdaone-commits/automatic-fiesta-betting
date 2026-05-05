import json
import logging
import time
from typing import Dict

from core.config import Config

logger = logging.getLogger(__name__)


class TelegramStatusMixin:
    """Mixin for status, performance, history and error commands."""

    def _enhanced_status(self) -> str:
        """Enhanced /status with mode, websocket state, wallet, balance, recent errors."""
        lines = ["*📊 Statut du Bot*\n"]
        
        # 1. Mode actuel
        if Config.SIMULATION_MODE or not Config.LIVE_TRADING:
            mode_emoji = "🧪"
            mode_text = "SIMULATION"
            live_confirmed = False
        else:
            mode_emoji = "🔴"
            mode_text = "RÉEL (LIVE)"
            live_confirmed = Config.CONFIRM_LIVE_TRADING
        
        lines.append(f"{mode_emoji} *Mode*: {mode_text}")
        if mode_text == "RÉEL (LIVE)" and not live_confirmed:
            lines.append("⚠️ *CONFIRM_LIVE_TRADING* non défini - Trading désactivé")
        lines.append("")
        
        # 2. État WebSocket
        heartbeat_file = Config.DATA_DIR / "monitor_heartbeat.json"
        ws_status = "❌ Déconnecté"
        ws_block = "N/A"
        ws_messages = 0
        paused = False
        
        if heartbeat_file.exists():
            try:
                with open(heartbeat_file, 'r') as f:
                    heartbeat = json.load(f)
                    age = time.time() - heartbeat.get("timestamp", 0)
                    if age < 60:
                        ws_status = "✅ Connecté" if heartbeat.get("running") else "⏸️ En pause"
                        ws_block = heartbeat.get("block_height", "N/A")
                        ws_messages = heartbeat.get("messages_count", 0)
                        paused = heartbeat.get("paused", False)
                    else:
                        ws_status = f"⚠️ Dernier heartbeat il y a {int(age/60)} min"
            except Exception:
                ws_status = "⚠️ Erreur lecture heartbeat"
        
        lines.append(f"🌐 *WebSocket*: {ws_status}")
        lines.append(f"📦 Block: {ws_block} | Messages: {ws_messages}")
        lines.append(f"⏸️ *Pause*: {'OUI' if paused else 'NON'}")
        lines.append("")
        
        # 3. Wallet suivi
        wallets = Config.TARGET_WALLETS or []
        if wallets:
            lines.append(f"👛 *Wallets suivis* ({len(wallets)}):")
            for w in wallets[:5]:
                short = f"{w[:8]}...{w[-6:]}" if len(w) > 14 else w
                lines.append(f"  • `{short}`")
            if len(wallets) > 5:
                lines.append(f"  ... et {len(wallets) - 5} autres")
        else:
            lines.append("👛 *Wallets suivis*: Aucun")
        lines.append("")
        
        # 4. Balance
        try:
            from services.copy_trade import PolymarketTrader
            trader = PolymarketTrader(mode='test')
            balance_info = trader.check_cash_balance()
            if balance_info:
                balance = float(balance_info.get('balance', 0))
                lines.append(f"💰 *Balance*: ${balance:.2f} USDC")
            else:
                lines.append("💰 *Balance*: Erreur de lecture")
        except Exception as e:
            lines.append(f"💰 *Balance*: Indisponible ({str(e)[:30]})")
        lines.append("")
        
        # 5. Erreurs récentes
        log_file = Config.LOG_DIR / 'polymarket_follower.log'
        recent_errors = []
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines_log = f.readlines()
                    error_lines = [l.strip() for l in lines_log[-100:] if "ERROR" in l]
                    recent_errors = error_lines[-3:]
            except Exception:
                pass
        
        if recent_errors:
            lines.append("*⚠️ Erreurs récentes*:")
            for err in recent_errors:
                parts = err.split(" - ")
                if len(parts) > 3:
                    err_short = parts[-1][:80]
                    lines.append(f"  • {err_short}")
        else:
            lines.append("*✅ Aucune erreur récente*")
        
        return "\n".join(lines)

    def _toggle_pause_resume(self) -> str:
        """Toggle pause/resume state via bot_control.json."""
        control_file = Config.DATA_DIR / "bot_control.json"
        paused = False
        
        if control_file.exists():
            try:
                with open(control_file, 'r') as f:
                    control = json.load(f)
                    paused = control.get("paused", False)
            except Exception:
                pass
        
        new_paused = not paused
        
        try:
            with open(control_file, 'w') as f:
                json.dump({"paused": new_paused, "timestamp": time.time()}, f)
            
            if new_paused:
                return "⏸️ *Trading en PAUSE*\n\nLes nouveaux paris ne seront pas copiés.\nUtilise '▶️ Reprendre' pour continuer."
            else:
                return "▶️ *Trading REPREND*\n\nLes nouveaux paris seront copiés normalement."
        except Exception as e:
            return f"❌ Erreur lors du changement d'état: {e}"

    def _performance_text(self) -> str:
        """Show trading performance."""
        from services.jsonl_logger import read_records
        
        lines = ["*📈 Performance du Bot*\n"]
        
        trades = read_records("trades", limit=1000)
        
        if not trades:
            lines.append("Aucun trade enregistré pour le moment.")
            return "\n".join(lines)
        
        total_trades = len(trades)
        simulated = sum(1 for t in trades if t.get("simulation") or t.get("simulated"))
        live = total_trades - simulated
        success = sum(1 for t in trades if t.get("success"))
        failed = total_trades - success
        
        total_pnl = sum(float(t.get("pnl", 0) or 0) for t in trades)
        total_volume = sum(float(t.get("size", 0) or 0) for t in trades)
        
        success_rate = (success / total_trades * 100) if total_trades > 0 else 0
        
        lines.append(f"📊 *Total paris*: {total_trades}")
        lines.append(f"  • 🧪 Simulés: {simulated}")
        lines.append(f"  • 🔴 Live: {live}")
        lines.append("")
        lines.append(f"✅ *Succès*: {success} ({success_rate:.1f}%)")
        lines.append(f"❌ *Échecs*: {failed}")
        lines.append("")
        lines.append(f"💰 *PnL estimé*: ${total_pnl:.2f}")
        lines.append(f"📦 *Volume total*: ${total_volume:.2f}")
        
        return "\n".join(lines)

    def _history_text(self, page: int = 0, page_size: int = 5) -> str:
        """Show last trades with pagination."""
        from services.jsonl_logger import read_records
        
        lines = ["*📜 Historique des Paris*\n"]
        
        trades = read_records("trades", limit=100)
        
        if not trades:
            lines.append("Aucun historique disponible.")
            return "\n".join(lines)
        
        trades = list(reversed(trades))
        
        start = page * page_size
        end = start + page_size
        page_trades = trades[start:end]
        
        if not page_trades:
            lines.append("Plus de trades disponibles.")
            return "\n".join(lines)
        
        for trade in page_trades:
            side_emoji = "🟢" if trade.get("side") == "BUY" else "🔴"
            sim_label = "🧪" if trade.get("simulation") or trade.get("simulated") else "🔴"
            size = float(trade.get("size", 0) or 0)
            token_short = str(trade.get("token_id", ""))[:8] + "..."
            lines.append(f"{side_emoji} {sim_label} {trade.get('side')} ${size:.2f} sur {token_short}")
            lines.append(f"  Wallet: `{trade.get('wallet', 'N/A')[:10]}...`")
        
        lines.append("")
        total_pages = (len(trades) + page_size - 1) // page_size
        lines.append(f"Page {page + 1}/{total_pages}")
        
        return "\n".join(lines)

    def _wallet_history_text(self, page: int = 0, page_size: int = 10) -> str:
        """Show wallet-centric trade history with PnL stats from Polymarket API."""
        from services.jsonl_logger import read_records
        import requests
        
        wallet = self._active_wallet()
        if not wallet:
            return ("⚠️ *Aucun wallet actif*\n\n"
                    "Sélectionne un wallet pour voir l'historique.")
        
        short = f"{wallet[:6]}...{wallet[-4:]}"
        lines = [
            "*📜 Historique Polymarket*\n",
            f"⭐ *Wallet ETH*",
            f"Adresse: `{wallet}`\n",
        ]
        
        # 1. Fetch data from Polymarket Data API (public, no auth)
        from core.config import Config
        data_api = getattr(Config, 'DATA_API_HOST', 'https://data-api.polymarket.com').rstrip('/')
        
        try:
            # Open positions
            pos_resp = requests.get(f"{data_api}/positions", 
                                     params={"user": wallet, "limit": 100}, timeout=10)
            positions = pos_resp.json() if pos_resp.status_code == 200 else []
            
            # Closed positions  
            closed_resp = requests.get(f"{data_api}/closed-positions",
                                        params={"user": wallet, "limit": 100}, timeout=10)
            closed_positions = closed_resp.json() if closed_resp.status_code == 200 else []
            
            # Calculate stats
            open_count = len(positions)
            closed_count = len(closed_positions)
            total_volume = sum(float(p.get("size", 0) or 0) * float(p.get("avgPrice", 0) or 0) 
                               for p in (positions + closed_positions))
            realized_pnl = sum(float(p.get("realizedPnl", 0) or 0) for p in closed_positions)
            
            lines.append(f"Volume total: ${total_volume:.2f}")
            lines.append(f"Positions ouvertes: {open_count}")
            lines.append(f"Positions clôturées: {closed_count}")
            
            pnl_emoji = "🟢" if realized_pnl >= 0 else "🔴"
            lines.append(f"{pnl_emoji} PnL réalisé estimé: ${realized_pnl:+.2f}")
            lines.append(f"{pnl_emoji} Total estimé: ${realized_pnl:+.2f}\n")
            
        except Exception as e:
            logger.warning("Failed to fetch Polymarket data: %s", e)
            lines.append("⚠️ Données Polymarket indisponibles\n")
        
        # 2. Add trade history from local JSONL (bot's recorded trades)
        trades = read_records("trades", limit=100)
        wallet_trades = [t for t in trades if t.get("wallet", "").lower() == wallet.lower()]
        
        if not wallet_trades:
            lines.append("Aucun historique local disponible.")
            return "\n".join(lines)
        
        # Reverse full list so newest trades come first
        wallet_trades = list(reversed(wallet_trades))
        
        # Pagination with bounds checking
        total_trades = len(wallet_trades)
        self._history_total_pages = max(1, (total_trades + page_size - 1) // page_size)
        
        # Clamp page to valid range
        page = max(0, min(page, self._history_total_pages - 1))
        self._history_page = page
        
        start = page * page_size
        end = min(start + page_size, total_trades)
        
        page_trades = wallet_trades[start:end]
        
        lines.append("━━━━━━━━━━━━")
        lines.append(f"Page {page + 1}/{self._history_total_pages} - Trades {start + 1}-{end}/{total_trades}\n")
        
        for trade in page_trades:
            market = trade.get("market", "Marché inconnu")[:50]
            side = trade.get("side", "BUY")
            outcome = trade.get("outcome", "N/A")
            size = float(trade.get("size", 0) or 0)
            price = float(trade.get("price", 0) or 0)
            date = trade.get("_iso", "")[:16].replace("T", " ") if trade.get("_iso") else "N/A"
            
            side_emoji = "🟢" if side == "BUY" else "🔴"
            lines.append(f"{side_emoji} *{market}*")
            lines.append(f"• Side: {side}")
            lines.append(f"• Outcome: {outcome}")
            lines.append(f"• Size: {size:.2f}")
            lines.append(f"• Price: {price:.2f}")
            lines.append(f"• Date: {date}\n")
        
        return "\n".join(lines)

    def _mirrors_performance_text(self) -> str:
        """Analyze performance of all followed wallets."""
        from services.jsonl_logger import get_wallets_performance
        
        perf = get_wallets_performance()
        if not perf:
            return "❌ Aucun historique de trade disponible pour analyse."
            
        lines = ["*📊 Analyse de Rentabilité (CopyBet)*\n"]
        
        # Sort by PnL desc
        sorted_wallets = sorted(perf.items(), key=lambda x: x[1]['pnl'], reverse=True)
        
        for wallet, stats in sorted_wallets[:10]:
            pnl = stats['pnl']
            emoji = "✅" if pnl > 0 else "❌"
            recommendation = "💎 Très intéressant" if pnl > 50 else "👍 Intéressant" if pnl > 0 else "⚠️ À surveiller" if pnl > -50 else "🚫 Pas rentable"
            
            lines.append(f"{emoji} `{wallet[:10]}...` ({stats['trades']} trades)")
            lines.append(f"  • PnL: *{pnl:+.2f} USDC*")
            lines.append(f"  • Win rate: {stats['success_rate']:.1f}%")
            lines.append(f"  • Avis: *{recommendation}*")
            lines.append("")
            
        return "\n".join(lines)

    def _errors_text(self, limit: int = 10) -> str:
        """Show last errors from log files."""
        lines = ["*⚠️ Erreurs Récentes*\n"]
        
        log_file = Config.LOG_DIR / 'polymarket_follower.log'
        telegram_log = Config.LOG_DIR / 'telegram_bot.log'
        
        errors = []
        
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines_log = f.readlines()
                    error_lines = [l.strip() for l in lines_log[-500:] if "ERROR" in l or "CRITICAL" in l]
                    errors.extend(error_lines[-limit//2:] if len(error_lines) > limit//2 else error_lines)
            except Exception:
                pass
        
        if telegram_log.exists():
            try:
                with open(telegram_log, 'r', encoding='utf-8') as f:
                    lines_log = f.readlines()
                    error_lines = [l.strip() for l in lines_log[-500:] if "ERROR" in l or "CRITICAL" in l]
                    errors.extend(error_lines[-limit//2:] if len(error_lines) > limit//2 else error_lines)
            except Exception:
                pass
        
        if not errors:
            lines.append("✅ Aucune erreur récente trouvée.")
        else:
            lines.append(f"📋 *{len(errors)} erreurs récentes*:")
            for err in errors[-limit:]:
                parts = err.split(" - ")
                if len(parts) >= 4:
                    err_short = parts[3][:80]
                    lines.append(f"  • {err_short}")
                else:
                    lines.append(f"  • {err[:80]}")
        
        return "\n".join(lines)
