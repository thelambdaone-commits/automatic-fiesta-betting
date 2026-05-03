import logging
import sys
from pathlib import Path


def setup_logging(log_dir: Path, module_name: str = "polymarket"):
    """Setup logging with RotatingFileHandler."""
    from logging.handlers import RotatingFileHandler
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    console_handler = logging.StreamHandler()
    file_handler = RotatingFileHandler(
        log_dir / f'{module_name}.log',
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5,
        encoding='utf-8'
    )
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[console_handler, file_handler]
    )
    
    return logging.getLogger(module_name)


class LoggerMixin:
    """Mixin to add logging capability."""
    @property
    def logger(self):
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(type(self).__name__)
        return self._logger
