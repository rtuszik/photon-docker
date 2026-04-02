import re

from src.utils import config
from src.utils.logger import get_logger
from src.utils.regions import get_regions_for_jsonl, is_valid_region

logging = get_logger()


def validate_config():
    logging.info("Validating environment variables...")
    error_messages = []

    valid_import_modes = ["db", "jsonl"]
    if config.IMPORT_MODE not in valid_import_modes:
        error_messages.append(f"Invalid IMPORT_MODE: '{config.IMPORT_MODE}'. Must be one of {valid_import_modes}.")

    valid_strategies = ["SEQUENTIAL", "PARALLEL", "DISABLED"]
    if config.UPDATE_STRATEGY not in valid_strategies:
        error_messages.append(
            f"Invalid UPDATE_STRATEGY: '{config.UPDATE_STRATEGY}'. Must be one of {valid_strategies}."
        )

    if not re.match(r"^\d+[dhm]$", config.UPDATE_INTERVAL):
        error_messages.append(
            f"Invalid UPDATE_INTERVAL format: '{config.UPDATE_INTERVAL}'. Expected format like '30d', '12h', or '30m'."
        )

    if config.IMPORT_MODE == "db":
        if config.REGION and not is_valid_region(config.REGION):
            error_messages.append(
                f"Invalid REGION: '{config.REGION}'. Must be a valid continent, sub-region, or 'planet'."
            )
        if config.REGION and len(config.get_jsonl_regions()) > 1:
            error_messages.append("DB mode supports exactly one region in REGION.")

    if config.IMPORT_MODE == "jsonl":
        if config.FILE_URL:
            error_messages.append("FILE_URL is not supported when IMPORT_MODE=jsonl.")
        if config.MD5_URL:
            error_messages.append("MD5_URL is not supported when IMPORT_MODE=jsonl.")
        if not config.get_jsonl_regions():
            error_messages.append("REGION is required when IMPORT_MODE=jsonl.")
        else:
            try:
                validated_regions = get_regions_for_jsonl(config.get_jsonl_regions())
                if len(validated_regions) != 1:
                    error_messages.append("JSONL mode currently supports exactly one region.")
            except ValueError as exc:
                error_messages.append(str(exc))

    if error_messages:
        full_error_message = "Configuration validation failed:\n" + "\n".join(error_messages)
        raise ValueError(full_error_message)

    logging.info("Environment variables are valid.")
