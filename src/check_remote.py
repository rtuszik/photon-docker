import datetime
import os

import requests
from dateutil.parser import parse as parsedate
from requests.exceptions import RequestException

from src.utils import config
from src.utils.logger import get_logger
from src.utils.regions import get_region_info, normalize_region

logging = get_logger()


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

    except Exception as e:
        logging.warning(f"Could not determine remote file size for {url}: {e}")

    return 0


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
    if config.REGION:
        normalized = normalize_region(config.REGION)
        region_info = get_region_info(config.REGION)
        if not region_info:
            logging.error(f"Unknown region: {config.REGION}")
            return False

        region_type = region_info["type"]

        if region_type == "planet":
            index_file = "/photon-db-planet-0.7OS-latest.tar.bz2"
        elif region_type == "continent":
            index_file = f"/{normalized}/photon-db-{normalized}-0.7OS-latest.tar.bz2"
        elif region_type == "sub-region":
            continent = region_info["continent"]
            index_file = f"/{continent}/{normalized}/photon-db-{normalized}-0.7OS-latest.tar.bz2"
        else:
            logging.error(f"Invalid region type: {region_type}")
            return False
    else:
        index_file = "/photon-db-planet-0.7OS-latest.tar.bz2"

    remote_url = config.BASE_URL.rstrip("/") + index_file

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
