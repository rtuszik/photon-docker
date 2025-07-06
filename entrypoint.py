# contains the container startup logic. 
# If possible, create cronjob
# Check for existing index
# Check for Force update env var
# Download index if not exists

from src import config
from src.logger import get_logger
from src.downloader import sequential_update
from src.process import start_photon
import os

logging = get_logger()


def main():
    if not config.FORCE_UPDATE and os.path.isdir(config.OS_NODE_DIR):
        logging.info("Existing index found")
        start_cronjob()
        start_photon()
    else: 
        sequential_update()
        start_photon()



def check_for_index():
    if os.path.isdir(config.OS_NODE_DIR):
        existing 
    #verifies structure of the final extracted index



