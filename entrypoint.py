
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
