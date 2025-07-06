
import sys
from src.utils import config
from src.utils.validate_config import validate_config
from src.utils.logger import get_logger
from src.downloader import sequential_update, parallel_update
from src.process import start_photon
from src.cron_setup import setup_cronjob
import os

logging = get_logger()


def main():
    try:
        validate_config()
    except ValueError as e:
        logging.error(f"Stopping due to invalid configuration.\n{e}")
        sys.exit(1) 

    if not config.FORCE_UPDATE and os.path.isdir(config.OS_NODE_DIR):
        logging.info("Existing index found")
        setup_cronjob()
        start_photon()

    elif config.UPDATESTRATEGY == "SEQUENTIAL":
        parallel_update()
        setup_cronjob()
        start_photon()
    
    else:
        setup_cronjob()
        start_photon()
        sequential_update()
