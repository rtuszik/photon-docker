from src.utils.logger import get_logger
from src.utils.notify import send_notification
from src import config
from src.downloader import parallel_update, sequential_update
from src.check_remote import check_mtime
import sys

logger = get_logger()

def main():
    """Main updater function - handles both parallel and sequential updates"""
    logger.info("Starting update process...")
    
    try:
        # Check if update is needed
        if not check_mtime():
            logger.info("Index already up to date")
            return
        
        # Run the appropriate update strategy
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
    main()