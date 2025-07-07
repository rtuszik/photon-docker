import os
import shutil
import sys

import requests
from tqdm import tqdm

from src.filesystem import extract_index, move_index, verify_checksum, clear_temp_dir
from src.supervisor import stop_photon
from src.utils import config
from src.utils.logger import get_logger

logging = get_logger()

def parallel_update():
    logging.info("Starting parallel update process...")

    try:
        if os.path.isdir(config.TEMP_DIR):
            logging.debug(f"Temporary directory {config.TEMP_DIR} exists. Attempting to remove it.")
            try:
                shutil.rmtree(config.TEMP_DIR)
                logging.debug(f"Successfully removed directory: {config.TEMP_DIR}")
            except Exception as e:
                logging.error(f"Failed to remove existing TEMP_DIR: {e}")
                raise 

        logging.debug(f"Creating temporary directory: {config.TEMP_DIR}")
        os.makedirs(config.TEMP_DIR, exist_ok=True)

        logging.info("Downloading index")

        index_file = download_index()

        extract_index(index_file)

        if not config.SKIP_MD5_CHECK:
            md5_file = download_md5()

            logging.info("Verifying checksum...")
            verify_checksum(md5_file, index_file)

            logging.debug("Checksum verification successful.")

        logging.info("Stopping Photon")
        stop_photon()

        logging.info("Moving Index")
        move_index()
        clear_temp_dir()

        logging.info("Parallel update process completed successfully.")

    except Exception as e:
        logging.error(f"FATAL: Update process failed with an error: {e}")
        logging.error("Aborting script.")
        sys.exit(1) 

def sequential_update():
    logging.info("Starting sequential download process...")

    try:
        logging.info("Stopping Photon service before download...")
        stop_photon()

        # stop photon first
        logging.info("Deleting old index...")


        if os.path.isdir(config.TEMP_DIR):
            logging.debug(f"Temporary directory {config.TEMP_DIR} exists. Attempting to remove it.")
            try:
                shutil.rmtree(config.TEMP_DIR)
                logging.debug(f"Successfully removed directory: {config.TEMP_DIR}")
            except Exception as e:
                logging.error(f"Failed to remove existing TEMP_DIR: {e}")
                raise 

        logging.debug(f"Creating temporary directory: {config.TEMP_DIR}")
        os.makedirs(config.TEMP_DIR, exist_ok=True)

        logging.info("Downloading new index and MD5 checksum...")
        index_file = download_index()
        extract_index(index_file)

        if not config.SKIP_MD5_CHECK:
            md5_file = download_md5()

            logging.info("Verifying checksum...")
            verify_checksum(md5_file, index_file)

            logging.debug("Checksum verification successful.")

        logging.info("Moving new index into place...")
        move_index()

        clear_temp_dir()

        logging.info("Sequential download process completed successfully.")

    except Exception as e:
        logging.critical(f"FATAL: Update process failed with an error: {e}")
        logging.critical("Aborting script.")
        sys.exit(1) 

def download_index() -> str:
    
    if config.COUNTRY_CODE:
        index_file = "photon-db-" + config.COUNTRY_CODE + "-latest.tar.bz2"
        index_url = "/extracts/by-country-code/" + config.COUNTRY_CODE + "/" + index_file
    else: 
        index_file = "photon-db-latest.tar.bz2"
        index_url = "/photon-db-latest.tar.bz2"

    output_file = "photon-db-latest.tar.bz2"
    download_url = config.BASE_URL + index_url

    output = os.path.join(config.TEMP_DIR, output_file)
    
    download_file(download_url, output)
    
    return output

def download_md5():

    if config.COUNTRY_CODE:
        md5_file = "photon-db-" + config.COUNTRY_CODE + "-latest.tar.bz2.md5"
        md5_url = "/extracts/by-country-code/" + config.COUNTRY_CODE + "/" + md5_file
    else: 
        md5_file = "photon-db-latest.tar.bz2.md5"
        md5_url = "/photon-db-latest.tar.bz2.md5"

    download_url = config.BASE_URL + md5_url

    output_file = "photon-db-latest.tar.bz2.md5"
    output = os.path.join(config.TEMP_DIR, output_file)
    
    download_file(download_url, output)
    
    return output


def download_file(url, destination):
    # destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            
            # Create progress bar only if we know the total size
            progress_bar = None
            if total_size > 0:
                progress_bar = tqdm(
                    desc=f"Downloading {destination.name if hasattr(destination, 'name') else destination}",
                    total=total_size,
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                    leave=True
                )
            
            with open(destination, 'wb') as f:
                downloaded = 0
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        size = f.write(chunk)
                        downloaded += size
                        if progress_bar:
                            progress_bar.update(size)
                
                if progress_bar:
                    progress_bar.close()
                    
        logging.info(f"Downloaded {destination} successfully.")
        return True
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Download Failed: {e}")
        return False
