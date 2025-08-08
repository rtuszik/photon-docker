import hashlib
import os
import shutil
import subprocess
from pathlib import Path

from src.utils import config
from src.utils.logger import get_logger

logging = get_logger()


def extract_index(index_file: str):
    logging.info("Extracting Index")
    logging.debug(f"Index file: {index_file}")
    logging.debug(f"Index file exists: {os.path.exists(index_file)}")
    logging.debug(f"Index file size: {os.path.getsize(index_file) if os.path.exists(index_file) else 'N/A'}")
    logging.debug(f"Temp directory: {config.TEMP_DIR}")
    logging.debug(f"Temp directory exists: {os.path.exists(config.TEMP_DIR)}")

    if not os.path.exists(config.TEMP_DIR):
        logging.debug(f"Creating temp directory: {config.TEMP_DIR}")
        os.makedirs(config.TEMP_DIR, exist_ok=True)

    install_command = f"lbzip2 -d -c {index_file} | tar x -C {config.TEMP_DIR}"
    logging.debug(f"Extraction command: {install_command}")

    try:
        logging.debug("Starting extraction process...")
        result = subprocess.run(install_command, shell=True, capture_output=True, text=True, check=True)
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
                        for sub_item in sub_items[:5]:
                            logging.debug(f"      {sub_item}")
                        if len(sub_items) > 5:
                            logging.debug(f"      ... and {len(sub_items) - 5} more items")
                    except Exception as e:
                        logging.debug(f"    Could not list subdirectory contents: {e}")
                else:
                    logging.debug(f"  FILE: {item} ({os.path.getsize(item_path)} bytes)")
        except Exception as e:
            logging.debug(f"Could not list contents of {config.TEMP_DIR}: {e}")

    except subprocess.CalledProcessError as e:
        logging.error(f"Index extraction failed with return code {e.returncode}")
        logging.error(f"Command: {e.cmd}")
        logging.error(f"Stdout: {e.stdout}")
        logging.error(f"Stderr: {e.stderr}")
        raise
    except Exception:
        logging.exception("Index extraction failed")
        raise


def move_index():
    temp_photon_dir = os.path.join(config.TEMP_DIR, "photon_data")
    target_node_dir = os.path.join(config.PHOTON_DATA_DIR)

    logging.info(f"Moving index from {temp_photon_dir} to {target_node_dir}")
    result = move_index_atomic(temp_photon_dir, target_node_dir)

    if result:
        update_timestamp_marker()

    return result


def move_index_atomic(source_dir: str, target_dir: str) -> bool:
    try:
        logging.info("Starting atomic index move operation")

        os.makedirs(os.path.dirname(target_dir), exist_ok=True)

        staging_dir = target_dir + ".staging"
        backup_dir = target_dir + ".backup"

        cleanup_staging_and_temp_backup(staging_dir, backup_dir)

        shutil.move(source_dir, staging_dir)

        if os.path.exists(target_dir):
            os.rename(target_dir, backup_dir)

        os.rename(staging_dir, target_dir)
        logging.info("Atomic index move completed successfully")

        return True

    except Exception as e:
        logging.error(f"Atomic move failed: {e}")
        rollback_atomic_move(source_dir, target_dir, staging_dir, backup_dir)
        raise


def rollback_atomic_move(original_source: str, target_dir: str, staging_dir: str, backup_dir: str):
    logging.error("Rolling back atomic move operation")

    try:
        if os.path.exists(target_dir) and not os.path.exists(backup_dir):
            logging.debug("New index was successfully moved, keeping it")
            return

        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)

        if os.path.exists(backup_dir):
            logging.info("Restoring backup after failed atomic move")
            os.rename(backup_dir, target_dir)

        if os.path.exists(staging_dir):
            shutil.move(staging_dir, original_source)

        logging.info("Rollback completed successfully")

    except Exception as rollback_error:
        logging.critical(f"Rollback failed: {rollback_error}")


def cleanup_staging_and_temp_backup(staging_dir: str, backup_dir: str):
    for dir_path in [staging_dir, backup_dir]:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
            except Exception as e:
                logging.warning(f"Failed to cleanup {dir_path}: {e}")


def cleanup_backup_after_verification(target_dir: str) -> bool:
    backup_dir = target_dir + ".backup"
    if os.path.exists(backup_dir):
        try:
            logging.info("Removing backup after successful verification")
            shutil.rmtree(backup_dir)
            return True
        except Exception as e:
            logging.warning(f"Failed to cleanup backup: {e}")
            return False
    return True


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
        with open(md5_file) as f:
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
        logging.exception("Failed to Remove TEMP_DIR")


def update_timestamp_marker():
    marker_file = os.path.join(config.DATA_DIR, ".photon-index-updated")
    try:
        Path(marker_file).touch()
        logging.info(f"Updated timestamp marker: {marker_file}")
    except Exception as e:
        logging.warning(f"Failed to update timestamp marker: {e}")
