from src.utils.logger import get_logger
from src import config
from src.downloader import parallel_update, sequential_update
from src.process import start_photon
from src.check_remote import check_mtime
import sys

logging = get_logger()

def main():

    if not check_mtime():
        logging.info("Index already up to date")
        sys.exit(0)


    # CHECK IF PARALLEL OR DEFAULT TO SEQUENTIAL (check for disabled in crontab setup)
    if config.UPDATE_STRATEGY == "PARALLEL":
        parallel_update()
        start_photon()
    else:
        sequential_update()
        start_photon()

