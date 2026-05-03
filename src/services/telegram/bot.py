# Main Telegram bot file - uses new modular structure
import sys
from pathlib import Path

# Add necessary paths
ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"
SCRIPTS_DIR = ROOT_DIR / "scripts"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Use absolute imports for PM2 compatibility
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from core.config import Config
from services.telegram.core.bot_core import TelegramBotCore

# Import all mixins for backwards compatibility
from services.telegram.activity import TelegramActivityMixin
from services.telegram.api import TelegramApiMixin
from services.telegram.callbacks import CallbackHandler
from services.telegram.copy_handlers import TelegramCopyMixin
from services.telegram.keyboards import MainKeyboardMixin as TelegramKeyboardMixin
from services.telegram.manual import TelegramManualMixin
from services.telegram.market import TelegramMarketMixin
from services.telegram.risk import TelegramRiskMixin
from services.telegram.settings_mixin import TelegramSettingsMixin
from services.telegram.status import TelegramStatusMixin
from services.telegram.top_wallets import TelegramTopWalletsMixin
from services.telegram.ui.home import home_text as home_text_func
from services.telegram.wallet import TelegramWalletMixin
from services.groq_advisor import GroqAdvisor
from services.wallet_ranker import THEME_DETAIL_DISPLAY_LIMIT, THEME_RANK_LIMIT, WalletRanker

logger = __import__('logging').getLogger(__name__)


class TelegramControlBot(
    TelegramBotCore,
    TelegramKeyboardMixin,
    TelegramApiMixin,
    TelegramMarketMixin,
    TelegramTopWalletsMixin,
    TelegramCopyMixin,
    TelegramRiskMixin,
    TelegramWalletMixin,
    TelegramManualMixin,
    TelegramActivityMixin,
    TelegramStatusMixin,
    TelegramSettingsMixin,
):
    """Main bot class with all mixins for backwards compatibility."""
    
    def __init__(
        self,
        token: str = None,
        chat_id: str = None,
        request_timeout: int = 20,
    ):
        super().__init__(token=token, chat_id=chat_id, request_timeout=request_timeout)
        
    def handle_action(self, action: str) -> str:
        """Override to add custom actions."""
        # Handle custom actions not in core
        if action == "scan_wallet":
            return self.scan_wallet_text()
        if action.startswith("theme_"):
            theme_map = {
                "theme_politique": ("election politics president", "Politique"),
                "theme_sport": ("sports nba football champions", "Sport"),
                "theme_crypto": ("bitcoin ethereum solana crypto", "Crypto"),
                "theme_world": ("geopolitics economy world news", "Monde"),
            }
            if action in theme_map:
                keywords, label = theme_map[action]
                return self._search_markets(keywords, label=label)
        
        # Call parent handler
        return super().handle_action(action)

    def home_text(self) -> str:
        """Generate home screen text."""
        return home_text_func()


def main():
    """Main entry point for Telegram bot."""
    from logging.handlers import RotatingFileHandler
    from core.config import Config
    
    Config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    console_handler = logging.StreamHandler()
    file_handler = RotatingFileHandler(
        Config.LOG_DIR / 'telegram_bot.log',
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[console_handler, file_handler]
    )
    
    TelegramControlBot().run_forever()


if __name__ == "__main__":
    main()
