import hashlib
import shutil
import subprocess

from src.utils import config
from src.utils.logger import get_logger

logging = get_logger()

def extract_index(index_file: str):
    logging.info("Extracting Index")
    install_command = f"lbzip2 -d -c {index_file} | tar x -C {config.TEMP_DIR}"
    try:

        subprocess.run(install_command, shell=True, capture_output=True, text=True, check=True)

    except Exception as e:
        logging.error(f"Index extraction failed: {e}")
        raise

def move_index():
    logging.info(f"Moving Index from {config.TEMP_DIR} to {config.PHOTON_DATA_DIR} ")
    try:
        shutil.move(config.TEMP_DIR, config.PHOTON_DATA_DIR)
    except Exception:
        logging.error("Meeep")
        raise

def verify_checksum(md5_file, index_file):
    hash_md5 = hashlib.md5()
    try:
        with open(index_file, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        dl_sum = hash_md5.hexdigest()
    except FileNotFoundError:
        logging.error(f"Index file not found for checksum generation: {index_file}")
        raise

    try:
        with open(md5_file, 'r') as f:
            md5_sum = f.read().split()[0].strip()
    except FileNotFoundError:
        logging.error(f"MD5 file not found: {md5_file}")
        raise
    except IndexError:
        logging.error(f"MD5 file is empty or malformed: {md5_file}")
        raise

    if dl_sum == md5_sum:
        logging.info("Checksum verified successfully.")
        return True

    raise Exception(f"Checksum mismatch for {index_file}. Expected: {md5_sum}, Got: {dl_sum}")

