import sys
import os
from src.utils import config
from src.utils.validate_config import validate_config
from src.utils.logger import get_logger
from src.downloader import sequential_update, parallel_update
from src.utils.notify import send_notification

logger = get_logger()


def run_setup():
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
    logger.debug(f"PHOTON_DIR: {config.PHOTON_DIR}")
    logger.debug(f"PHOTON_DATA_DIR: {config.PHOTON_DATA_DIR}")
    logger.debug(f"TEMP_DIR: {config.TEMP_DIR}")
    logger.debug(f"OS_NODE_DIR: {config.OS_NODE_DIR}")
    logger.debug(f"PID_FILE: {config.PID_FILE}")
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
        except Exception:
            logger.error("Force update failed")
            raise
    elif not os.path.isdir(config.OS_NODE_DIR):
        logger.info("Starting initial download")
        sequential_update()
    else:
        logger.info("Existing index found, skipping download")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        run_setup()
    else:
        run_setup()


if __name__ == "__main__":
    main()
