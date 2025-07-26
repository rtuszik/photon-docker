import hashlib
import os
import shutil
import subprocess

from src.utils import config
from src.utils.logger import get_logger

logging = get_logger()


def extract_index(index_file: str):
    logging.info("Extracting Index")
    logging.debug(f"Index file: {index_file}")
    logging.debug(f"Index file exists: {os.path.exists(index_file)}")
    logging.debug(
        f"Index file size: {os.path.getsize(index_file) if os.path.exists(index_file) else 'N/A'}"
    )
    logging.debug(f"Temp directory: {config.TEMP_DIR}")
    logging.debug(f"Temp directory exists: {os.path.exists(config.TEMP_DIR)}")

    if not os.path.exists(config.TEMP_DIR):
        logging.debug(f"Creating temp directory: {config.TEMP_DIR}")
        os.makedirs(config.TEMP_DIR, exist_ok=True)

    # using shell=true for piping, could construct pipe directly in the future...
    install_command = f"lbzip2 -d -c {index_file} | tar x -C {config.TEMP_DIR}"
    logging.debug(f"Extraction command: {install_command}")

    try:
        logging.debug("Starting extraction process...")
        result = subprocess.run(
            install_command, shell=True, capture_output=True, text=True, check=True
        )
        logging.debug("Extraction process completed successfully")

        if result.stdout:
            logging.debug(f"Extraction stdout: {result.stdout}")
        if result.stderr:
            logging.debug(f"Extraction stderr: {result.stderr}")

        logging.debug(f"Contents of {config.TEMP_DIR} after extraction:")
        try:
            for item in os.listdir(config.TEMP_DIR):
                item_path = os.path.join(config.TEMP_DIR, item)
                if os.path.isdir(item_path):
                    logging.debug(f"  DIR: {item}")
                    try:
                        sub_items = os.listdir(item_path)
                        logging.debug(f"    Contains {len(sub_items)} items")
                        for sub_item in sub_items[:5]:  # Show first 5 items
                            logging.debug(f"      {sub_item}")
                        if len(sub_items) > 5:
                            logging.debug(
                                f"      ... and {len(sub_items) - 5} more items"
                            )
                    except Exception as e:
                        logging.debug(f"    Could not list subdirectory contents: {e}")
                else:
                    logging.debug(
                        f"  FILE: {item} ({os.path.getsize(item_path)} bytes)"
                    )
        except Exception as e:
            logging.debug(f"Could not list contents of {config.TEMP_DIR}: {e}")

    except subprocess.CalledProcessError as e:
        logging.error(f"Index extraction failed with return code {e.returncode}")
        logging.error(f"Command: {e.cmd}")
        logging.error(f"Stdout: {e.stdout}")
        logging.error(f"Stderr: {e.stderr}")
        raise
    except Exception as e:
        logging.error(f"Index extraction failed: {e}")
        raise


def move_index():

    logging.debug(f"Contents of source directory {config.TEMP_DIR}:")
    try:
        for item in os.listdir(config.TEMP_DIR):
            item_path = os.path.join(config.TEMP_DIR, item)
            if os.path.isdir(item_path):
                logging.debug(f"  DIR: {item}")
            else:
                logging.debug(f"  FILE: {item}")
    except Exception as e:
        logging.debug(f"Could not list contents of {config.TEMP_DIR}: {e}")

    logging.debug(
        f"Destination directory {config.PHOTON_DATA_DIR} exists: {os.path.exists(config.PHOTON_DATA_DIR)}"
    )
    if os.path.exists(config.PHOTON_DATA_DIR):
        logging.debug(f"Contents of destination directory {config.PHOTON_DATA_DIR}:")
        try:
            for item in os.listdir(config.PHOTON_DATA_DIR):
                item_path = os.path.join(config.PHOTON_DATA_DIR, item)
                if os.path.isdir(item_path):
                    logging.debug(f"  DIR: {item}")
                else:
                    logging.debug(f"  FILE: {item}")
        except Exception as e:
            logging.debug(f"Could not list contents of {config.PHOTON_DATA_DIR}: {e}")

    temp_photon_dir = os.path.join(config.TEMP_DIR, "photon_data/node_1")
    target_node_dir = os.path.join(config.PHOTON_DATA_DIR, "node_1")

    try:
        logging.debug(f"Attempting to move {temp_photon_dir} to {target_node_dir}")
        
        if os.path.exists(target_node_dir):
            backup_dir = target_node_dir + ".old"
            
            if os.path.exists(backup_dir):
                logging.debug(f"Removing old backup directory: {backup_dir}")
                shutil.rmtree(backup_dir)
            
            logging.debug(f"Moving current index to backup: {target_node_dir} -> {backup_dir}")
            shutil.move(target_node_dir, backup_dir)
            
            try:
                shutil.move(temp_photon_dir, target_node_dir)
                logging.debug(f"Successfully moved new index to {target_node_dir}")
                
                logging.debug(f"Removing backup directory: {backup_dir}")
                shutil.rmtree(backup_dir)
                
            except Exception as e:
                logging.error(f"Failed to move new index: {e}")
                logging.error("Attempting to restore backup...")
                if os.path.exists(backup_dir):
                    if os.path.exists(target_node_dir):
                        shutil.rmtree(target_node_dir)
                    shutil.move(backup_dir, target_node_dir)
                raise
        else:
            os.makedirs(config.PHOTON_DATA_DIR, exist_ok=True)
            shutil.move(temp_photon_dir, target_node_dir)
            logging.debug(f"Successfully moved new index to {target_node_dir}")

        logging.debug(
            f"Contents of final destination {config.PHOTON_DATA_DIR} after move:"
        )
        try:
            for item in os.listdir(config.PHOTON_DATA_DIR):
                item_path = os.path.join(config.PHOTON_DATA_DIR, item)
                if os.path.isdir(item_path):
                    logging.debug(f"  DIR: {item}")
                else:
                    logging.debug(f"  FILE: {item}")
        except Exception as e:
            logging.debug(
                f"Could not list contents of {config.PHOTON_DATA_DIR} after move: {e}"
            )

    except Exception as e:
        logging.error(
            f"Failed to move index from {temp_photon_dir} to {target_node_dir}: {e}"
        )
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
        with open(md5_file, "r") as f:
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

    raise Exception(
        f"Checksum mismatch for {index_file}. Expected: {md5_sum}, Got: {dl_sum}"
    )


def clear_temp_dir():
    logging.info("Removing TEMP dir")
    if os.path.exists(config.TEMP_DIR):
        logging.debug(f"Contents of TEMP directory {config.TEMP_DIR}:")
        try:
            for item in os.listdir(config.TEMP_DIR):
                item_path = os.path.join(config.TEMP_DIR, item)
                if os.path.isdir(item_path):
                    logging.debug(f"  DIR: {item}")
                else:
                    logging.debug(f"  FILE: {item}")
        except Exception as e:
            logging.debug(f"Could not list contents of {config.TEMP_DIR}: {e}")

    try:
        shutil.rmtree(config.TEMP_DIR)
    except Exception:
        logging.error("Failed to Remove TEMP_DIR")
