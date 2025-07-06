import datetime
import os

import requests
from dateutil.parser import parse as parsedate

from utils import config
from utils.logger import get_logger

logging = get_logger()

def get_remote_time(remote_url: str):
    try:
        r = requests.head(remote_url, timeout=10)
        r.raise_for_status()
        urltime = r.headers.get('last-modified')
        if urltime:
            return parsedate(urltime)
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching remote URL: {e}")
    return None

def get_local_time(local_path: str):
    if not os.path.exists(local_path):
        return 0.0 
    return os.path.getmtime(local_path)

def compare_mtime() -> bool:

    if config.COUNTRY_CODE:
        index_file = "/extracts/by-country-code/" + config.COUNTRYCODE + "/photon-db-" + config.COUNTRYCODE + "-latest.tar.bz2"

    else:
        index_file = "/photon-db-latest.tar.bz2" 

    remote_url = os.path.join(config.BASE_URL, index_file)

    remote_dt = get_remote_time(remote_url) 
    
    if remote_dt is None:
        logging.warning("Could not determine remote time. Assuming no update is needed.")
        return False

    local_timestamp = get_local_time(config.OS_NODE_DIR) 

    local_dt = datetime.datetime.fromtimestamp(local_timestamp, tz=datetime.timezone.utc)

    grace_period = datetime.timedelta(hours=24)

    logging.debug(f"Remote index time: {remote_dt}")
    logging.debug(f"Local index time:  {local_dt}")
    
    return remote_dt > (local_dt + grace_period)
