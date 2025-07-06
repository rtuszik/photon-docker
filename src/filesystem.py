import subprocess
from utils import config
from utils.logger import get_logger
import hashlib
import shutil

logging = get_logger()

def extract_index(index_file):
    install_command = "lbzip2 dc " + index_file + " | tar -x -C " + config.TEMP_DIR
    try:

        subprocess.run([install_command], shell=True, capture_output=True, text=True, check=True)

    except Exception:
        logging.error("Index extraction failed")


def move_index():
    logging.info(f"Moving Index from {config.TEMP_DIR} to {config.PHOTON_DATA_DIR} ")
    try:
        shutil.move(config.TEMP_DIR, config.PHOTON_DATA_DIR)
    except Exception:
        logging.error("Meeep")




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

    # Get expected checksum from the .md5 file
    try:
        with open(md5_file, 'r') as f:
            md5_sum = f.read().split()[0].strip()
    except FileNotFoundError:
        logging.error(f"MD5 file not found: {md5_file}")
        raise
    except IndexError:
        logging.error(f"MD5 file is empty or malformed: {md5_file}")
        raise

    # Compare generated and expected checksums
    if dl_sum == md5_sum:
        logging.info("Checksum verified successfully.")
        return True

    raise Exception(f"Checksum mismatch for {index_file}. Expected: {md5_sum}, Got: {dl_sum}")

