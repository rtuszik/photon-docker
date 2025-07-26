import json
import os
import shutil
import sys

import requests
from requests.exceptions import RequestException
from tqdm import tqdm

from src.filesystem import clear_temp_dir, extract_index, move_index, verify_checksum
from src.check_remote import get_local_time, get_remote_file_size
from src.utils import config
from src.utils.logger import get_logger

logging = get_logger()


def get_available_space(path: str) -> int:
    try:
        statvfs = os.statvfs(path)
        return statvfs.f_frsize * statvfs.f_bavail
    except (OSError, AttributeError):
        return 0


def get_directory_size(path: str) -> int:
    if not os.path.exists(path):
        return 0
    
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(file_path)
                except (OSError, FileNotFoundError):
                    continue
    except (OSError, PermissionError):
        pass
    
    return total_size


def check_disk_space_requirements(download_size: int, is_parallel: bool = True) -> bool:
    temp_available = get_available_space(config.TEMP_DIR if os.path.exists(config.TEMP_DIR) else config.DATA_DIR)
    data_available = get_available_space(config.PHOTON_DATA_DIR if os.path.exists(config.PHOTON_DATA_DIR) else config.DATA_DIR)
    
    compressed_size = download_size
    extracted_size = int(download_size * 1.65)
    
    if is_parallel:
        temp_needed = compressed_size + extracted_size
        data_needed = extracted_size
        total_needed = int(download_size * 1.7)
        
        logging.info("Parallel update space requirements:")
        logging.info(f"  Download size: {compressed_size / (1024**3):.2f} GB")
        logging.info(f"  Estimated extracted size: {extracted_size / (1024**3):.2f} GB")
        logging.info(f"  Total space needed: {total_needed / (1024**3):.2f} GB")
        logging.info(f"  Temp space available: {temp_available / (1024**3):.2f} GB")
        logging.info(f"  Data space available: {data_available / (1024**3):.2f} GB")
        
        if temp_available < temp_needed:
            logging.error(f"Insufficient temp space: need {temp_needed / (1024**3):.2f} GB, have {temp_available / (1024**3):.2f} GB")
            return False
            
        if data_available < data_needed:
            logging.error(f"Insufficient data space: need {data_needed / (1024**3):.2f} GB, have {data_available / (1024**3):.2f} GB")
            return False
            
    else:
        temp_needed = compressed_size + extracted_size
        
        logging.info("Sequential update space requirements:")
        logging.info(f"  Download size: {compressed_size / (1024**3):.2f} GB")
        logging.info(f"  Estimated extracted size: {extracted_size / (1024**3):.2f} GB")
        logging.info(f"  Temp space needed: {temp_needed / (1024**3):.2f} GB")
        logging.info(f"  Temp space available: {temp_available / (1024**3):.2f} GB")
        
        if temp_available < temp_needed:
            logging.error(f"Insufficient temp space: need {temp_needed / (1024**3):.2f} GB, have {temp_available / (1024**3):.2f} GB")
            return False
    
    logging.info("Sufficient disk space available for update")
    return True

def get_download_state_file(destination: str) -> str:
    return destination + ".download_state"


def save_download_state(destination: str, url: str, downloaded_bytes: int, total_size: int):
    state_file = get_download_state_file(destination)
    state = {
        "url": url,
        "destination": destination,
        "downloaded_bytes": downloaded_bytes,
        "total_size": total_size,
        "file_size": os.path.getsize(destination) if os.path.exists(destination) else 0
    }
    try:
        with open(state_file, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        logging.warning(f"Failed to save download state: {e}")


def load_download_state(destination: str) -> dict:
    state_file = get_download_state_file(destination)
    if not os.path.exists(state_file):
        return {}
    
    try:
        with open(state_file, 'r') as f:
            state = json.load(f)
            
        if os.path.exists(destination):
            actual_size = os.path.getsize(destination)
            if state.get("file_size", 0) == actual_size:
                return state
            else:
                logging.warning("File size mismatch, starting fresh download")
                cleanup_download_state(destination)
        
    except Exception as e:
        logging.warning(f"Failed to load download state: {e}")
        cleanup_download_state(destination)
    
    return {}


def cleanup_download_state(destination: str):
    state_file = get_download_state_file(destination)
    try:
        if os.path.exists(state_file):
            os.remove(state_file)
    except Exception as e:
        logging.warning(f"Failed to cleanup download state: {e}")


def supports_range_requests(url: str) -> bool:
    try:
        response = requests.head(url, allow_redirects=True)
        response.raise_for_status()
        return response.headers.get('accept-ranges', '').lower() == 'bytes'
    except Exception as e:
        logging.warning(f"Could not determine range support for {url}: {e}")
        return False


def get_download_url() -> str:
    if config.COUNTRY_CODE:
        index_file = "photon-db-" + config.COUNTRY_CODE + "-latest.tar.bz2"
        index_url = (
            "/extracts/by-country-code/" + config.COUNTRY_CODE + "/" + index_file
        )
    else:
        index_file = "photon-db-latest.tar.bz2"
        index_url = "/photon-db-latest.tar.bz2"

    return config.BASE_URL + index_url


def parallel_update():
    logging.info("Starting parallel update process...")

    try:
        if os.path.isdir(config.TEMP_DIR):
            logging.debug(
                f"Temporary directory {config.TEMP_DIR} exists. Attempting to remove it."
            )
            try:
                shutil.rmtree(config.TEMP_DIR)
                logging.debug(f"Successfully removed directory: {config.TEMP_DIR}")
            except Exception as e:
                logging.error(f"Failed to remove existing TEMP_DIR: {e}")
                raise

        logging.debug(f"Creating temporary directory: {config.TEMP_DIR}")
        os.makedirs(config.TEMP_DIR, exist_ok=True)

        download_url = get_download_url()
        file_size = get_remote_file_size(download_url)
        
        if file_size > 0:
            if not check_disk_space_requirements(file_size, is_parallel=True):
                logging.error("Insufficient disk space for parallel update")
                sys.exit(1)
        else:
            logging.warning("Could not determine download size, proceeding without space check")

        logging.info("Downloading index")

        index_file = download_index()

        extract_index(index_file)

        if not config.SKIP_MD5_CHECK:
            md5_file = download_md5()

            logging.info("Verifying checksum...")
            verify_checksum(md5_file, index_file)

            logging.debug("Checksum verification successful.")

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
        logging.info("Deleting old index...")

        if os.path.isdir(config.TEMP_DIR):
            logging.debug(
                f"Temporary directory {config.TEMP_DIR} exists. Attempting to remove it."
            )
            try:
                shutil.rmtree(config.TEMP_DIR)
                logging.debug(f"Successfully removed directory: {config.TEMP_DIR}")
            except Exception as e:
                logging.error(f"Failed to remove existing TEMP_DIR: {e}")
                raise

        logging.debug(f"Creating temporary directory: {config.TEMP_DIR}")
        os.makedirs(config.TEMP_DIR, exist_ok=True)

        download_url = get_download_url()
        file_size = get_remote_file_size(download_url)
        
        if file_size > 0:
            if not check_disk_space_requirements(file_size, is_parallel=False):
                logging.error("Insufficient disk space for sequential update")
                sys.exit(1)
        else:
            logging.warning("Could not determine download size, proceeding without space check")

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
        index_url = (
            "/extracts/by-country-code/" + config.COUNTRY_CODE + "/" + index_file
        )
    else:
        index_file = "photon-db-latest.tar.bz2"
        index_url = "/photon-db-latest.tar.bz2"

    output_file = "photon-db-latest.tar.bz2"
    download_url = config.BASE_URL + index_url

    output = os.path.join(config.TEMP_DIR, output_file)

    download_file(download_url, output)

    local_timestamp = get_local_time(config.OS_NODE_DIR)

    logging.debug(f"New index timestamp: {local_timestamp}")
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


def download_file(url, destination, max_retries=3):
    state = load_download_state(destination)
    resume_byte_pos = 0
    mode = "wb"
    
    if state and state.get("url") == url:
        resume_byte_pos = state.get("downloaded_bytes", 0)
        if resume_byte_pos > 0 and os.path.exists(destination):
            mode = "ab"
            logging.info(f"Resuming download from byte {resume_byte_pos}")
    
    for attempt in range(max_retries):
        try:
            headers = {}
            if resume_byte_pos > 0 and supports_range_requests(url):
                headers['Range'] = f'bytes={resume_byte_pos}-'
            
            with requests.get(url, stream=True, headers=headers) as r:
                r.raise_for_status()
                
                if headers and r.status_code == 206:
                    content_range = r.headers.get('content-range', '')
                    if content_range:
                        total_size = int(content_range.split('/')[-1])
                    else:
                        total_size = resume_byte_pos + int(r.headers.get("content-length", 0))
                else:
                    total_size = int(r.headers.get("content-length", 0))
                    if resume_byte_pos > 0:
                        logging.warning("Server doesn't support range requests, restarting download")
                        resume_byte_pos = 0
                        mode = "wb"
                        if os.path.exists(destination):
                            os.remove(destination)

                progress_bar = None
                if total_size > 0:
                    progress_bar = tqdm(
                        desc=f"Downloading {os.path.basename(destination)}",
                        total=total_size,
                        initial=resume_byte_pos,
                        unit="B",
                        unit_scale=True,
                        unit_divisor=1024,
                        leave=True,
                    )

                downloaded = resume_byte_pos
                chunk_size = 8192
                save_interval = 1024 * 1024  # Save state every 1MB
                last_save = downloaded

                with open(destination, mode) as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if chunk:
                            size = f.write(chunk)
                            downloaded += size
                            if progress_bar:
                                progress_bar.update(size)
                            
                            if downloaded - last_save >= save_interval:
                                save_download_state(destination, url, downloaded, total_size)
                                last_save = downloaded

                    if progress_bar:
                        progress_bar.close()

                save_download_state(destination, url, downloaded, total_size)
                
                if total_size > 0 and downloaded < total_size:
                    raise Exception(f"Download incomplete: {downloaded}/{total_size} bytes")

                cleanup_download_state(destination)
                logging.info(f"Downloaded {destination} successfully.")
                return True

        except RequestException as e:
            logging.error(f"Download attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                logging.info(f"Retrying download (attempt {attempt + 2}/{max_retries})...")
                continue
            else:
                logging.error(f"Download failed after {max_retries} attempts")
                return False
        except Exception as e:
            logging.error(f"Download failed: {e}")
            return False

    return False
