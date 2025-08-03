import os
import sys

from .downloader import InsufficientSpaceError, parallel_update, sequential_update
from .utils import config
from .utils.logger import get_logger, setup_logging
from .utils.notify import send_notification
from .utils.validate_config import validate_config

logger = get_logger()


def main():
    send_notification("Photon-Docker Initializing")

    logger.debug("Entrypoint setup called")
    logger.debug("=== CONFIG VARIABLES ===")
    logger.debug(f"UPDATE_STRATEGY: {config.UPDATE_STRATEGY}")
    logger.debug(f"UPDATE_INTERVAL: {config.UPDATE_INTERVAL}")
    logger.debug(f"COUNTRY_CODE: {config.COUNTRY_CODE}")
    logger.debug(f"FORCE_UPDATE: {config.FORCE_UPDATE}")
    logger.debug(f"FILE_URL: {config.FILE_URL}")
    logger.debug(f"PHOTON_PARAMS: {config.PHOTON_PARAMS}")
    logger.debug(f"JAVA_PARAMS: {config.JAVA_PARAMS}")
    logger.debug(f"LOG_LEVEL: {config.LOG_LEVEL}")
    logger.debug(f"BASE_URL: {config.BASE_URL}")
    logger.debug(f"SKIP_MD5_CHECK: {config.SKIP_MD5_CHECK}")

    logger.debug("=== END CONFIG VARIABLES ===")

    try:
        validate_config()
    except ValueError as e:
        logger.error(f"Stopping due to invalid configuration.\n{e}")
        sys.exit(1)

    if config.FORCE_UPDATE:
        logger.info("Starting forced update")
        try:
            if config.UPDATE_STRATEGY == "PARALLEL":
                parallel_update()
            else:
                sequential_update()
        except InsufficientSpaceError as e:
            logger.error(f"Cannot proceed with force update: {e}")
            send_notification(f"Photon-Docker force update failed: {e}")
            sys.exit(75)
        except Exception:
            logger.error("Force update failed")
            raise
    elif not os.path.isdir(config.OS_NODE_DIR):
        logger.info("Starting initial download")
        try:
            sequential_update()
        except InsufficientSpaceError as e:
            logger.error(f"Cannot proceed: {e}")
            send_notification(f"Photon-Docker cannot start: {e}")
            sys.exit(75)
    else:
        logger.info("Existing index found, skipping download")


if __name__ == "__main__":
    setup_logging()
    main()
