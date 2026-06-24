from src import index
from src.check_remote import check_index_age
from src.importer import run_jsonl_import
from src.update import InsufficientSpaceError, run_update
from src.utils import config
from src.utils.logger import get_logger
from src.utils.notify import send_notification
from src.utils.sanitize import sanitize_url
from src.utils.validate_config import validate_config

logger = get_logger()


def log_config() -> None:
    logger.info("=== CONFIG VARIABLES ===")
    logger.info(f"IMPORT_MODE: {config.IMPORT_MODE}")
    logger.info(f"UPDATE_STRATEGY: {config.UPDATE_STRATEGY}")
    logger.info(f"UPDATE_INTERVAL: {config.UPDATE_INTERVAL}")
    logger.info(f"REGION: {config.REGION}")
    logger.info(f"LANGUAGES: {config.LANGUAGES}")
    logger.info(f"EXTRA_TAGS: {config.EXTRA_TAGS}")
    logger.info(f"IMPORT_GEOMETRIES: {config.IMPORT_GEOMETRIES}")
    logger.info(f"REVERSE_ONLY: {config.REVERSE_ONLY}")
    logger.info(f"FORCE_UPDATE: {config.FORCE_UPDATE}")
    logger.info(f"DOWNLOAD_MAX_RETRIES: {config.DOWNLOAD_MAX_RETRIES}")
    logger.info(f"CHECKSUM_MAX_RETRIES: {config.CHECKSUM_MAX_RETRIES}")
    logger.info(f"FILE_URL (sanitized): {sanitize_url(config.FILE_URL)}")
    logger.info(f"MD5_URL (sanitized): {sanitize_url(config.MD5_URL)}")
    logger.info(f"PHOTON_PARAMS: {config.PHOTON_PARAMS}")
    logger.info(f"ENABLE_METRICS: {config.ENABLE_METRICS}")
    logger.info(f"JAVA_PARAMS: {config.JAVA_PARAMS}")
    logger.info(f"LOG_LEVEL: {config.LOG_LEVEL}")
    logger.info(f"BASE_URL: {config.BASE_URL}")
    logger.info(f"SKIP_MD5_CHECK: {config.SKIP_MD5_CHECK}")
    logger.info(f"INITIAL_DOWNLOAD: {config.INITIAL_DOWNLOAD}")
    logger.info(f"SKIP_SPACE_CHECK: {config.SKIP_SPACE_CHECK}")
    if config.APPRISE_URLS:
        logger.info("APPRISE_URLS: REDACTED")
    else:
        logger.info("APPRISE_URLS: UNSET")

    logger.info("=== END CONFIG VARIABLES ===")


def run_update_or_import(*, force_update: bool = False) -> None:
    if config.IMPORT_MODE == "jsonl":
        action = "forced JSONL import" if force_update else "initial JSONL import"
        logger.info(f"Starting {action}")
        run_jsonl_import()
        return

    if not force_update:
        logger.info("Starting initial download using sequential strategy")
        logger.info("Note: Initial download will use sequential strategy regardless of config setting")
        run_update("SEQUENTIAL")
        return

    run_update("PARALLEL" if config.UPDATE_STRATEGY == "PARALLEL" else "SEQUENTIAL")


def run_setup() -> None:
    send_notification("Photon-Docker Initializing")

    log_config()
    validate_config()

    if config.MIN_INDEX_DATE:
        logger.info(f"MIN_INDEX_DATE: {config.MIN_INDEX_DATE}")

    index.reconcile()

    if config.FORCE_UPDATE:
        logger.info("Starting forced update")
        try:
            run_update_or_import(force_update=True)
        except InsufficientSpaceError as e:
            logger.error(f"Cannot proceed with force update: {e}")
            send_notification(f"Photon-Docker force update failed: {e}")
            raise
        return

    if not index.is_present():
        if not config.INITIAL_DOWNLOAD:
            logger.warning("Initial download is disabled but no existing Photon index was found. ")
            return
        try:
            run_update_or_import(force_update=False)
        except InsufficientSpaceError as e:
            logger.error(f"Cannot proceed: {e}")
            send_notification(f"Photon-Docker cannot start: {e}")
            raise
        return

    logger.info("Existing index found, skipping download")

    if config.IMPORT_MODE == "jsonl":
        logger.info("JSONL mode with existing index found, skipping automatic rebuild during setup")
        return

    if config.MIN_INDEX_DATE and check_index_age():
        logger.info("Index is older than minimum required date, starting sequential update")
        try:
            run_update("SEQUENTIAL")
        except InsufficientSpaceError as e:
            logger.error(f"Cannot proceed with minimum date update: {e}")
            send_notification(f"Photon-Docker minimum date update failed: {e}")
            raise
