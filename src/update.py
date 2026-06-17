import hashlib
import os
import subprocess

from src import index
from src.check_remote import RemoteFileSizeError, get_remote_file_size
from src.downloader import check_disk_space_requirements, clear_temp_dir, download_file, prepare_temp_dir
from src.utils import config
from src.utils.logger import get_logger
from src.utils.notify import send_notification
from src.utils.regions import get_index_url_path
from src.utils.sanitize import sanitize_url

logging = get_logger()


class UpdateError(Exception):
    pass


class InsufficientSpaceError(UpdateError):
    pass


class DownloadError(UpdateError):
    pass


class ExtractionError(UpdateError):
    pass


class ChecksumMismatchError(UpdateError):
    pass


def get_download_url() -> str:
    if config.FILE_URL:
        logging.info("Using custom FILE_URL for download: %s", sanitize_url(config.FILE_URL))
        return config.FILE_URL

    index_path = get_index_url_path(config.REGION, config.INDEX_DB_VERSION, config.INDEX_FILE_EXTENSION)
    download_url = config.BASE_URL + index_path
    logging.info("Using constructed location for download: %s", sanitize_url(download_url))
    return download_url


def download_index() -> str:
    output_file = f"photon-db-latest.{config.INDEX_FILE_EXTENSION}"
    download_url = get_download_url()

    output = os.path.join(config.TEMP_DIR, output_file)

    if not download_file(download_url, output):
        raise DownloadError(f"Failed to download index from {sanitize_url(download_url)}")

    return output


def download_md5() -> str:
    if config.MD5_URL:
        logging.info("Using custom MD5_URL for checksum: %s", sanitize_url(config.MD5_URL))
        download_url = config.MD5_URL
    else:
        md5_path = get_index_url_path(config.REGION, config.INDEX_DB_VERSION, config.INDEX_FILE_EXTENSION) + ".md5"
        download_url = config.BASE_URL + md5_path
        logging.info("Using constructed URL for checksum: %s", sanitize_url(download_url))

    output_file = f"photon-db-latest.{config.INDEX_FILE_EXTENSION}.md5"
    output = os.path.join(config.TEMP_DIR, output_file)

    if not download_file(download_url, output):
        raise DownloadError(f"Failed to download MD5 checksum from {sanitize_url(download_url)}")

    return output


def extract_index(index_file: str):
    logging.info("Extracting Index")
    logging.debug(f"Index file: {index_file}")

    if not os.path.exists(config.TEMP_DIR):
        os.makedirs(config.TEMP_DIR, exist_ok=True)

    install_command = f"lbzip2 -d -c {index_file} | tar x -o -C {config.TEMP_DIR}"
    logging.debug(f"Extraction command: {install_command}")

    try:
        result = subprocess.run(  # noqa: S603
            ["/bin/bash", "-o", "pipefail", "-c", install_command], capture_output=True, text=True, check=True
        )
        if result.stderr:
            logging.debug(f"Extraction stderr: {result.stderr}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Index extraction failed with return code {e.returncode}")
        logging.error(f"Stderr: {e.stderr}")
        raise ExtractionError(f"Index extraction failed with return code {e.returncode}") from e


def verify_checksum(md5_file: str, index_file: str) -> bool:
    hash_md5 = hashlib.md5()  # noqa S303
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

    raise ChecksumMismatchError(f"Checksum mismatch for {index_file}. Expected: {md5_sum}, Got: {dl_sum}")


def _ensure_disk_space(download_url: str, *, parallel: bool):
    try:
        file_size = get_remote_file_size(download_url)
    except RemoteFileSizeError as e:
        if config.SKIP_SPACE_CHECK:
            logging.warning(f"{e}")
            logging.warning("SKIP_SPACE_CHECK is enabled, proceeding without space check")
            return
        logging.error(f"{e}")
        logging.error(
            "Cannot proceed without verifying disk space. "
            "Set SKIP_SPACE_CHECK=true to bypass this check (not recommended)."
        )
        raise UpdateError(str(e)) from e

    if not check_disk_space_requirements(file_size, is_parallel=parallel):
        raise InsufficientSpaceError("Insufficient disk space for update")


def _download_verified_index() -> str:
    max_attempts = max(1, int(config.CHECKSUM_MAX_RETRIES))

    for attempt in range(1, max_attempts + 1):
        logging.info("Downloading index")
        index_file = download_index()

        if config.SKIP_MD5_CHECK:
            return index_file

        md5_file = download_md5()
        logging.info("Verifying checksum...")
        try:
            verify_checksum(md5_file, index_file)
            return index_file
        except ChecksumMismatchError as e:
            if attempt >= max_attempts:
                logging.error(f"Checksum verification failed after {max_attempts} attempt(s): {e}")
                raise

            logging.warning(f"Checksum verification failed (attempt {attempt}/{max_attempts}), re-downloading: {e}")
            send_notification(
                f"Photon index download corrupted (checksum mismatch), re-downloading (attempt {attempt}/{max_attempts})"
            )

    raise UpdateError("Index download failed unexpectedly")


def run_update(strategy: str):
    logging.info(f"Starting {strategy.lower()} update pipeline...")

    prepare_temp_dir()

    download_url = get_download_url()
    _ensure_disk_space(download_url, parallel=strategy == "PARALLEL")

    index_file = _download_verified_index()

    extract_index(index_file)

    logging.info("Activating new index")
    index.activate(os.path.join(config.TEMP_DIR, "photon_data"))
    clear_temp_dir()

    logging.info("Update pipeline completed successfully.")
