import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

# Constants with sane defaults
DEFAULT_LOG_FILE = "app.log"
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB
DEFAULT_BACKUP_COUNT = 5
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

_logger: Optional[logging.Logger] = None

def setup_logging(
    log_file: str = os.getenv("LOG_FILE", DEFAULT_LOG_FILE),
) -> logging.Logger:
    """
    Configure and return a logger that:
    - Prints INFO and above to console
    - Writes DEBUG and above to rotating file
    """
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger("app")
    logger.setLevel(logging.DEBUG)  # Capture all levels
    
    # Create formatter
    formatter = logging.Formatter(DEFAULT_FORMAT)

    # Remove any existing handlers
    logger.handlers.clear()

    # Console handler (stdout) - INFO and above
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler - DEBUG and above
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=DEFAULT_MAX_BYTES,
            backupCount=DEFAULT_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except PermissionError:
        logger.warning(f"Unable to create/access log file: {log_file}")

    # Prevent logging from propagating to the root logger
    logger.propagate = False

    _logger = logger
    return logger

def get_logger() -> logging.Logger:
    """Get or create a logger instance."""
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger


