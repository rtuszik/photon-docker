import datetime
import os

import requests
from dateutil.parser import parse as parsedate
from requests.exceptions import RequestException

from src.utils import config
from src.utils.logger import get_logger
from src.utils.regions import get_index_url_path

logging = get_logger()


class RemoteFileSizeError(Exception):
    pass


def get_remote_file_size(url: str) -> int:
    try:
        response = requests.head(url, allow_redirects=True, timeout=15)
        response.raise_for_status()

        content_length = response.headers.get("content-length")
        if content_length:
            return int(content_length)

        response = requests.get(url, headers={"Range": "bytes=0-0"}, stream=True, timeout=15)
        response.raise_for_status()

        content_range = response.headers.get("content-range")
        if content_range and "/" in content_range:
            total_size = content_range.split("/")[-1]
            if total_size.isdigit():
                return int(total_size)

        raise RemoteFileSizeError(f"Server did not return file size for {url}")

    except RemoteFileSizeError:
        raise
    except Exception as e:
        raise RemoteFileSizeError(f"Could not determine remote file size for {url}: {e}") from e


def get_remote_time(remote_url: str):
    try:
        r = requests.head(remote_url, timeout=10)
        r.raise_for_status()
        urltime = r.headers.get("last-modified")
        if urltime:
            return parsedate(urltime)
    except RequestException as e:
        logging.exception(f"Error fetching remote URL: {e}")
    return None


def get_local_time(local_path: str):
    marker_file = os.path.join(config.DATA_DIR, ".photon-index-updated")
    if os.path.exists(marker_file):
        return os.path.getmtime(marker_file)

    if not os.path.exists(local_path):
        return 0.0
    return os.path.getmtime(local_path)


def compare_mtime() -> bool:
    try:
        index_path = get_index_url_path(config.REGION, config.INDEX_DB_VERSION, config.INDEX_FILE_EXTENSION)
    except ValueError as e:
        logging.error(str(e))
        return False

    remote_url = config.BASE_URL + index_path

    remote_dt = get_remote_time(remote_url)

    if remote_dt is None:
        logging.warning("Could not determine remote time. Assuming no update is needed.")
        return False

    marker_file = os.path.join(config.DATA_DIR, ".photon-index-updated")
    using_marker_file = os.path.exists(marker_file)

    local_timestamp = get_local_time(config.OS_NODE_DIR)
    local_dt = datetime.datetime.fromtimestamp(local_timestamp, tz=datetime.UTC)

    logging.debug(f"Remote index time: {remote_dt}")
    logging.debug(f"Local index time:  {local_dt}")

    if using_marker_file:
        logging.debug("Using marker file timestamp - comparing directly without grace period")
        return remote_dt > local_dt
    else:
        logging.debug("Using directory timestamp - applying 144-hour grace period")
        grace_period = datetime.timedelta(hours=144)
        return remote_dt > (local_dt + grace_period)


def check_index_age() -> bool:
    if not config.MIN_INDEX_DATE:
        return True

    try:
        min_date = datetime.datetime.strptime(config.MIN_INDEX_DATE, "%d.%m.%y").replace(tzinfo=datetime.UTC)
    except ValueError:
        logging.warning(f"Invalid MIN_INDEX_DATE format: {config.MIN_INDEX_DATE}. Expected DD.MM.YY")
        return True

    local_timestamp = get_local_time(config.OS_NODE_DIR)
    if local_timestamp == 0.0:
        logging.info("No local index found, update required")
        return True

    local_dt = datetime.datetime.fromtimestamp(local_timestamp, tz=datetime.UTC)

    logging.debug(f"Local index date: {local_dt.date()}")
    logging.debug(f"Minimum required date: {min_date.date()}")

    if local_dt < min_date:
        logging.info(f"Local index ({local_dt.date()}) is older than minimum required ({min_date.date()})")
        return True

    logging.info(f"Local index ({local_dt.date()}) meets minimum date requirement ({min_date.date()})")
    return False
