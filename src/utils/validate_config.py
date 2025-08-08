import re

from . import config
from .logger import get_logger

logging = get_logger()


def validate_config():
    logging.info("Validating environment variables...")
    error_messages = []

    valid_strategies = ["SEQUENTIAL", "PARALLEL", "DISABLED"]
    if config.UPDATE_STRATEGY not in valid_strategies:
        error_messages.append(
            f"Invalid UPDATE_STRATEGY: '{config.UPDATE_STRATEGY}'. Must be one of {valid_strategies}."
        )

    if not re.match(r"^\d+[dhm]$", config.UPDATE_INTERVAL):
        error_messages.append(
            f"Invalid UPDATE_INTERVAL format: '{config.UPDATE_INTERVAL}'. Expected format like '30d', '12h', or '30m'."
        )

    if error_messages:
        full_error_message = "Configuration validation failed:\n" + "\n".join(error_messages)
        raise ValueError(full_error_message)

    logging.info("Environment variables are valid.")
