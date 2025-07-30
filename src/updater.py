import sys

from .downloader import parallel_update, sequential_update
from .utils import config
from .utils.logger import get_logger, setup_logging
from .utils.notify import send_notification

logger = get_logger()


def main():
    """Main updater function - handles both parallel and sequential updates"""
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
        error_msg = f"Update failed: {str(e)}"
        logger.error(error_msg)
        send_notification(f"Photon Update Failed - {error_msg}")
        sys.exit(1)


if __name__ == "__main__":
    setup_logging()
    main()
