import os
import shutil
from pathlib import Path

from src.utils import config
from src.utils.logger import get_logger

logging = get_logger()


class IndexRollbackError(Exception):
    pass


def _updated_marker() -> str:
    return os.path.join(config.DATA_DIR, ".photon-index-updated")


def _import_in_progress_marker() -> str:
    return os.path.join(config.DATA_DIR, ".photon-import-in-progress")


def is_present() -> bool:
    return os.path.isdir(config.OS_NODE_DIR)


def has_update_timestamp() -> bool:
    return os.path.exists(_updated_marker())


def last_updated() -> float:
    marker_file = _updated_marker()
    if os.path.exists(marker_file):
        return os.path.getmtime(marker_file)

    if not os.path.exists(config.OS_NODE_DIR):
        return 0.0
    return os.path.getmtime(config.OS_NODE_DIR)


def mark_updated():
    marker_file = _updated_marker()
    try:
        Path(marker_file).touch()
        logging.info(f"Updated timestamp marker: {marker_file}")
    except Exception as e:
        logging.warning(f"Failed to update timestamp marker: {e}")


def begin_import():
    marker_file = _import_in_progress_marker()
    Path(marker_file).touch()
    logging.debug(f"Marked import in progress: {marker_file}")


def complete_import():
    mark_updated()
    _clear_import_marker()


def import_was_interrupted() -> bool:
    return os.path.exists(_import_in_progress_marker())


def reconcile():
    if not import_was_interrupted():
        return

    logging.warning(
        "Detected an interrupted import (in-progress marker present). "
        "Removing the partial index so a clean import can run."
    )
    if os.path.isdir(config.PHOTON_DATA_DIR):
        logging.warning(f"Removing incomplete index at {config.PHOTON_DATA_DIR}")
        shutil.rmtree(config.PHOTON_DATA_DIR)
    _clear_import_marker()


def activate(source_dir: str):
    target_dir = config.PHOTON_DATA_DIR
    staging_dir = target_dir + ".staging"
    backup_dir = target_dir + ".backup"

    try:
        logging.info(f"Activating new index from {source_dir}")

        os.makedirs(os.path.dirname(target_dir), exist_ok=True)

        _cleanup_staging_and_stale_backup(staging_dir, backup_dir)

        shutil.move(source_dir, staging_dir)

        if os.path.exists(target_dir):
            os.rename(target_dir, backup_dir)

        os.rename(staging_dir, target_dir)
        logging.info("Atomic index move completed successfully")

    except Exception as e:
        logging.error(f"Index activation failed: {e}")
        _rollback_activation(source_dir, target_dir, staging_dir, backup_dir)
        raise

    mark_updated()


def drop_backup() -> bool:
    backup_dir = config.PHOTON_DATA_DIR + ".backup"
    if os.path.exists(backup_dir):
        try:
            logging.info("Removing backup after successful verification")
            shutil.rmtree(backup_dir)
            return True
        except Exception as e:
            logging.warning(f"Failed to cleanup backup: {e}")
            return False
    return True


def _clear_import_marker():
    Path(_import_in_progress_marker()).unlink(missing_ok=True)


def _cleanup_staging_and_stale_backup(staging_dir: str, backup_dir: str):
    for dir_path in [staging_dir, backup_dir]:
        if os.path.exists(dir_path):
            logging.info(f"Removing leftover directory before activation: {dir_path}")
            shutil.rmtree(dir_path)


def _rollback_activation(original_source: str, target_dir: str, staging_dir: str, backup_dir: str):
    logging.error("Rolling back index activation")

    try:
        if os.path.exists(backup_dir):
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            logging.info("Restoring backup after failed activation")
            os.rename(backup_dir, target_dir)

        if os.path.exists(staging_dir) and not os.path.exists(original_source):
            shutil.move(staging_dir, original_source)

        logging.info("Rollback completed successfully")

    except Exception as rollback_error:
        logging.critical(f"Rollback failed, index state may be inconsistent: {rollback_error}")
        raise IndexRollbackError(
            f"Rollback after failed index activation also failed: {rollback_error}. "
            "Index state may be inconsistent and require manual intervention."
        ) from rollback_error
