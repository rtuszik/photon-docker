import logging
from . import config
import sys
from typing import Optional

# Constants with sane defaults
DEFAULT_LOG_FILE = "app.log"
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB
DEFAULT_BACKUP_COUNT = 5
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

_logger: Optional[logging.Logger] = None

def setup_logging(
) -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger("app")
    logger.setLevel(config.LOG_LEVEL)  # Capture all levels
    
    # Create formatter
    formatter = logging.Formatter(DEFAULT_FORMAT)

    # Remove any existing handlers
    logger.handlers.clear()

    # Console handler (stdout) - INFO and above
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(config.LOG_LEVEL)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Prevent logging from propagating to the root logger
    logger.propagate = False

    _logger = logger
    return logger

def get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger


