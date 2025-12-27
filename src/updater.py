import sys

from src.downloader import parallel_update, sequential_update
from src.utils import config
from src.utils.logger import get_logger, setup_logging
from src.utils.notify import send_notification

logger = get_logger()


def main():
    logger.info("Starting update process...")

    try:
        if config.UPDATE_STRATEGY == "PARALLEL":
            logger.info("Running parallel update...")
            parallel_update()
        elif config.UPDATE_STRATEGY == "SEQUENTIAL":
            logger.info("Running sequential update...")
            sequential_update()
        else:
            logger.error(f"Unknown update strategy: {config.UPDATE_STRATEGY}")
            sys.exit(1)

        logger.info("Update completed successfully")
        send_notification("Photon Index Updated Successfully")

    except Exception as e:
        error_msg = f"Update failed: {e!s}"
        logger.exception(error_msg)
        send_notification(f"Photon Update Failed - {error_msg}")
        sys.exit(1)


if __name__ == "__main__":
    setup_logging()
    main()
