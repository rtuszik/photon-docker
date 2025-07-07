
import sys
from src.utils import config
from src.utils.validate_config import validate_config
from src.utils.logger import get_logger
from src.downloader import sequential_update, parallel_update
from src.supervisor import start_photon
from src.cron_setup import setup_cronjob
import os

logging = get_logger()


def main():
    logging.debug("Entrypoint Called")
    
    # Debug: List all config variables
    logging.debug("=== CONFIG VARIABLES ===")
    logging.debug(f"UPDATE_STRATEGY: {config.UPDATE_STRATEGY}")
    logging.debug(f"UPDATE_INTERVAL: {config.UPDATE_INTERVAL}")
    logging.debug(f"COUNTRY_CODE: {config.COUNTRY_CODE}")
    logging.debug(f"FORCE_UPDATE: {config.FORCE_UPDATE}")
    logging.debug(f"FILE_URL: {config.FILE_URL}")
    logging.debug(f"PHOTON_PARAMS: {config.PHOTON_PARAMS}")
    logging.debug(f"JAVA_PARAMS: {config.JAVA_PARAMS}")
    logging.debug(f"LOG_LEVEL: {config.LOG_LEVEL}")
    logging.debug(f"BASE_URL: {config.BASE_URL}")
    logging.debug(f"SKIP_MD5_CHECK: {config.SKIP_MD5_CHECK}")
    logging.debug(f"PHOTON_DIR: {config.PHOTON_DIR}")
    logging.debug(f"PHOTON_DATA_DIR: {config.PHOTON_DATA_DIR}")
    logging.debug(f"TEMP_DIR: {config.TEMP_DIR}")
    logging.debug(f"OS_NODE_DIR: {config.OS_NODE_DIR}")
    logging.debug(f"PID_FILE: {config.PID_FILE}")
    logging.debug("=== END CONFIG VARIABLES ===")
    
    try:
        validate_config()
    except ValueError as e:
        logging.error(f"Stopping due to invalid configuration.\n{e}")
        sys.exit(1) 

    if not config.FORCE_UPDATE and os.path.isdir(config.OS_NODE_DIR):
        logging.info("Existing index found")
        setup_cronjob()
        start_photon()

    elif config.FORCE_UPDATE:
        logging.info("Starting forced update")
        try:
            if config.UPDATE_STRATEGY == "PARALLEL":
                parallel_update()
            else:
                sequential_update()
        except Exception:
            logging.error("Force update failed")
            raise 
    else:
        logging.debug("Starting Initial Download")
        sequential_update()
        setup_cronjob()
        start_photon()


if __name__ == "__main__":
    main()
