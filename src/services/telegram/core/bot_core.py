import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests

# Add necessary paths
ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"
SCRIPTS_DIR = ROOT_DIR / "scripts"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from core.config import Config
from .action_handler import ActionHandler
from .message_handler import MessageHandler
from .telegram_client import TelegramClient

logger = logging.getLogger(__name__)


class TelegramBotCore(TelegramClient, ActionHandler, MessageHandler):
    """Core bot functionality - initialization and main loop."""
    
    def __init__(
        self,
        token: Optional[str] = None,
        chat_id: Optional[str] = None,
        request_timeout: int = 20,
    ):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id_str = str(chat_id or os.getenv("TELEGRAM_CHAT_ID") or "")
        self.chat_ids = [cid.strip() for cid in chat_id_str.split(",") if cid.strip()]
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not self.chat_ids:
            raise ValueError("TELEGRAM_CHAT_ID is required")
        
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.request_timeout = request_timeout
        self.offset = 0
        
        # Initialize mixins
        TelegramClient.__init__(self)
        ActionHandler.__init__(self)
        
        # History pagination
        self._history_page = 0
        self._history_page_size = 5
        self._rank_scores = []
        self._rank_page = 0
        self._rank_display_limit = 10
        self._rank_selected_theme = ""
        self._whale_trades = []
        self._whale_page = 0
        
        # Settings
        self._settings_file = Config.CONFIG_DIR / "user_settings.json"
        self._user_settings = self._load_settings()
    
    def _load_settings(self) -> dict:
        """Load user settings from JSON file."""
        default_settings = {
            "mode": "simulation",
            "max_trade_usdc": 10.0,
            "slippage": "any",
            "risk_level": "safe",
            "default_wallet": "",
            "simulation": True,
            "live_trading": False,
        }
        if not self._settings_file.exists():
            return default_settings
        try:
            with open(self._settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key, value in default_settings.items():
                if key not in data:
                    data[key] = value
            return data
        except Exception as e:
            logger.warning("Failed to load settings: %s", e)
            return default_settings
    
    def _save_settings(self):
        """Save user settings to JSON file."""
        try:
            self._settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._settings_file, "w", encoding="utf-8") as f:
                json.dump(self._user_settings, f, indent=2)
        except Exception as e:
            logger.error("Failed to save settings: %s", e)
    
    def run_forever(self):
        """Main bot loop."""
        from services.telegram.ui.home import home_text
        from services.telegram.keyboards.main import MainKeyboardMixin
        keyboard = MainKeyboardMixin().keyboard()
        self.send_message(home_text(), reply_markup=keyboard)
        
        while True:
            try:
                for update in self.get_updates():
                    self.offset = max(self.offset, update["update_id"] + 1)
                    self.handle_update(update)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                logger.exception("Telegram bot error: %s", exc)
                time.sleep(5)
