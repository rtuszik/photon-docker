from src.utils.logger import get_logger
from src.utils.notify import send_notification
from src import config
from src.downloader import parallel_update, sequential_update
from src.process import start_photon
from src.check_remote import check_mtime
import sys

logging = get_logger()

def main():
    update_successful = False
    photon_started = False
    
    try:
        if not check_mtime():
            logging.info("Index already up to date")
            sys.exit(0)
        
        if config.UPDATE_STRATEGY == "PARALLEL":
            parallel_update()
        else:
            sequential_update()
        update_successful = True
        
        start_photon()
        photon_started = True
        
        send_notification("Photon Index Updated Successfully")
        
    except Exception as e:
        # error message based on failures
        if not update_successful:
            error_msg = f"Index update failed: {str(e)}"
        elif not photon_started:
            error_msg = f"Index updated but Photon failed to start: {str(e)}"
        else:
            error_msg = f"Unexpected error: {str(e)}"
            
        logging.error(error_msg)
        send_notification(f"Photon Update Failed - {error_msg}")
        raise
