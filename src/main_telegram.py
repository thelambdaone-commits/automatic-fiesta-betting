# Main entry point for Telegram bot - new modular structure
import logging
import sys
from pathlib import Path

# Add necessary paths
ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
SCRIPTS_DIR = ROOT_DIR / "scripts"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from logging.handlers import RotatingFileHandler
from core.config import Config

def main():
    """Main entry point for Telegram bot."""
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
    
    # Use the new modular bot
    from services.telegram.bot import TelegramControlBot
    TelegramControlBot().run_forever()


if __name__ == "__main__":
    main()
