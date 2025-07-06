# this is the entrypoint for the update script
# it should by called on the specified schedule with cronjob
# it will make use of the python-pidfile library to prevent multiple instances at the same time

from src.logger import get_logger
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


# check for existance of pidfile and run if no other instance running
# check if remote file newer than local file
# create update based on local function



