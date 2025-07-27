import logging
import logging.handlers
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from . import config

DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

_logger: Optional[logging.Logger] = None


class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "context"):
            log_entry["context"] = record.context

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


class ContextFilter(logging.Filter):
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.context = context or {}

    def filter(self, record):
        if self.context:
            record.context = self.context
        return True


def setup_logging() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger("app")
    logger.setLevel(config.LOG_LEVEL)
    logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(config.LOG_LEVEL)
    console_formatter = logging.Formatter(DEFAULT_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    try:
        log_dir = Path(config.DATA_DIR) / "logs"
        log_dir.mkdir(exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "photon.log",
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=5,
        )
        file_handler.setLevel(logging.INFO)

        if config.LOG_LEVEL == "DEBUG":
            file_handler.setFormatter(console_formatter)
        else:
            file_handler.setFormatter(StructuredFormatter())

        logger.addHandler(file_handler)
    except (OSError, PermissionError):
        pass

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    logger.propagate = False
    _logger = logger
    return logger


def get_logger(
    name: str = "app", context: Optional[Dict[str, Any]] = None
) -> logging.Logger:
    if name == "app":
        global _logger
        if _logger is None:
            _logger = setup_logging()
        return _logger

    logger = logging.getLogger(f"app.{name}")
    if context:
        for handler in logger.handlers:
            has_context_filter = any(
                isinstance(f, ContextFilter) and f.context == context
                for f in handler.filters
            )
            if not has_context_filter:
                handler.addFilter(ContextFilter(context))
    return logger


def get_component_logger(
    component_name: str, context: Optional[Dict[str, Any]] = None
) -> logging.Logger:
    base_context = {"component": component_name}
    if context:
        base_context.update(context)
    return get_logger(component_name, base_context)
