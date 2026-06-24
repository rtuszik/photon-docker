import re

from src.utils import config
from src.utils.logger import get_logger
from src.utils.regions import get_region_info, get_regions_for_jsonl, is_valid_region

logging = get_logger()


def _validate_db_mode() -> list[str]:
    errors = []

    if config.REGION and len(config.get_jsonl_regions()) > 1:
        errors.append("DB mode supports exactly one region in REGION.")
    elif config.REGION:
        if not is_valid_region(config.REGION):
            errors.append(f"Invalid REGION: '{config.REGION}'. Must be a valid continent, sub-region, or 'planet'.")
        else:
            region_info = get_region_info(config.REGION)
            if region_info and not region_info.get("db_available", False):
                errors.append(f"DB index is not available for REGION: '{config.REGION}'.")

    if config.REVERSE_ONLY:
        errors.append("REVERSE_ONLY is only supported when IMPORT_MODE=jsonl, since it is an import-time option.")

    return errors


def _validate_jsonl_mode() -> list[str]:
    errors = []

    if config.FILE_URL:
        errors.append("FILE_URL is not supported when IMPORT_MODE=jsonl.")
    if config.MD5_URL:
        errors.append("MD5_URL is not supported when IMPORT_MODE=jsonl.")
    if not config.get_jsonl_regions():
        errors.append("REGION is required when IMPORT_MODE=jsonl.")
    else:
        try:
            get_regions_for_jsonl(config.get_jsonl_regions())
        except ValueError as exc:
            errors.append(str(exc))

    return errors


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
        error_messages.extend(_validate_db_mode())

    if config.IMPORT_MODE == "jsonl":
        error_messages.extend(_validate_jsonl_mode())

    if error_messages:
        full_error_message = "Configuration validation failed:\n" + "\n".join(error_messages)
        raise ValueError(full_error_message)

    logging.info("Environment variables are valid.")
