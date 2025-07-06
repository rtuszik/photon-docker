import config
import sys
from logger import get_logger
from process import stop_photon
from filesystem import extract_index, move_index, verify_checksum
import os
import requests
import tqdm

logging = get_logger()

def parallel_update():
    logging.info("Starting parallel update process...")

    try:
        if os.path.isdir(config.TEMP_DIR):
            logging.debug(f"Temporary directory {config.TEMP_DIR} exists. Attempting to remove it.")
            try:
                os.removedirs(config.TEMP_DIR)
                logging.debug(f"Successfully removed directory: {config.TEMP_DIR}")
            except Exception as e:
                logging.error(f"Failed to remove existing TEMP_DIR: {e}")
                raise # Re-raising the exception after logging it

        logging.debug(f"Creating temporary directory: {config.TEMP_DIR}")
        os.makedir(config.TEMP_DIR, exist_ok=True)

        logging.info("Downloading index and MD5 checksum...")
        download_index()
        download_md5()

        logging.info("Verifying checksum...")

        verify_checksum()

        logging.debug("Checksum verification successful.")

        logging.info("Stopping Photon")
        stop_photon()

        logging.info("Moving Index")
        move_index()

        logging.info("Parallel update process completed successfully.")

    except Exception as e:
        logging.error(f"FATAL: Update process failed with an error: {e}")
        logging.error("Aborting script.")
        sys.exit(1) 

def sequential_download():
    logging.info("Starting sequential download process...")

    try:
        logging.info("Stopping Photon service before download...")
        stop_photon()

        # stop photon first
        logging.info("Deleting old index...")


        if os.path.isdir(config.TEMP_DIR):
            logging.debug(f"Temporary directory {config.TEMP_DIR} exists. Attempting to remove it.")
            try:
                os.removedirs(config.TEMP_DIR)
                logging.debug(f"Successfully removed directory: {config.TEMP_DIR}")
            except Exception as e:
                logging.error(f"Failed to remove existing TEMP_DIR: {e}")
                raise # Re-raising the exception is good practice

        logging.debug(f"Creating temporary directory: {config.TEMP_DIR}")
        os.makedir(config.TEMP_DIR, exist_ok=True)

        logging.info("Downloading new index and MD5 checksum...")
        download_index()
        extract_index()
        download_md5()

        logging.info("Verifying checksum...")
        verify_checksum()
        logging.debug("Checksum verification successful.")

        logging.info("Moving new index into place...")
        move_index()

        logging.info("Sequential download process completed successfully.")

    except Exception as e:
        logging.critical(f"FATAL: Update process failed with an error: {e}")
        logging.critical("Aborting script.")
        sys.exit(1) # Exit the script with an error code

def download_index():
    
    if config.COUNTRY_CODE:
        index_file = "extracts/by-country-code/" + config.COUNTRYCODE + "/photon-db-" + config.COUNTRYCODE + "-latest.tar.bz2"

    else:
        index_file = "photon-db-latest.tar.bz2" 

    download_url = config.BASE_URL + index_file
    
    output = config.TEMP + index_file
    
    download_file(download_url, output)

def download_md5():

    if config.COUNTRY_CODE:
        md5_file = "extracts/by-country-code/" + config.COUNTRYCODE + "/photon-db-" + config.COUNTRYCODE + "-latest.tar.bz2.md5"
    else: 
        md5_file = "photon-db-latest.tar.bz2.md5"

    download_url = config.BASE_URL + md5_file

    output = config.TEMP_DIR + md5_file
    
    download_file(download_url, output)


def download_file(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            
            with open(destination, 'wb') as f, tqdm(
                desc=destination.name,
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:
                for chunk in r.iter_content(chunk_size=8192):
                    size = f.write(chunk)
                    bar.update(size)
        logging.info(f"Downloaded {destination} successfully.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Download Failed: {e}")
        return False
    return True
    



