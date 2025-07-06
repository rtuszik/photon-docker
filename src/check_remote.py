import requests
from dateutil.parser import parse as parsedate
from logger import get_logger

logging = get_logger()

def get_remote_time(remote_url: str):
    r = requests.head(remote_url)
    urltime = r.headers['last-modified']
    url_date = parsedate(urltime)
    return url_date

def get_local_time():

    pass

def compare_mtime() -> bool:
    remote_time = get_remote_time()
    logging.debug(f"remote index time: {remote_time}")
    local_time = get_local_time()
    logging.debug(f"local index time: {local_time}")

    if remote_time > local_time:
        return True
    if local_time >= remote_time:
        return False

