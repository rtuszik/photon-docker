import os

# USER CONFIG
UPDATE_STRATEGY = os.getenv("UPDATE_STRATEGY", "SEQUENTIAL")
UPDATE_INTERVAL = os.getenv("UPDATE_INTERVAL", "30d")
REGION = os.getenv("REGION")
FORCE_UPDATE = os.getenv("FORCE_UPDATE", "False").lower() in ("true", "1", "t")
DOWNLOAD_MAX_RETRIES = os.getenv("DOWNLOAD_MAX_RETRIES", "3")
FILE_URL = os.getenv("FILE_URL")
MD5_URL = os.getenv("MD5_URL")
PHOTON_PARAMS = os.getenv("PHOTON_PARAMS")
ENABLE_METRICS = os.getenv("ENABLE_METRICS", "False").lower() in ("true", "1", "t")
JAVA_PARAMS = os.getenv("JAVA_PARAMS")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
BASE_URL = os.getenv("BASE_URL", "https://r2.koalasec.org/public").rstrip("/")
SKIP_MD5_CHECK = os.getenv("SKIP_MD5_CHECK", "False").lower() in ("true", "1", "t")
INITIAL_DOWNLOAD = os.getenv("INITIAL_DOWNLOAD", "True").lower() in ("true", "1", "t")
SKIP_SPACE_CHECK = os.getenv("SKIP_SPACE_CHECK", "False").lower() in ("true", "1", "t")
APPRISE_URLS = os.getenv("APPRISE_URLS")
MIN_INDEX_DATE = os.getenv("MIN_INDEX_DATE", "10.02.26")
PHOTON_LISTEN_IP = os.getenv("PHOTON_LISTEN_IP", "0.0.0.0")  # noqa: S104

# APP CONFIG
INDEX_DB_VERSION = "1.0"
INDEX_FILE_EXTENSION = "tar.bz2"

PHOTON_DIR = "/photon"
DATA_DIR = "/photon/data"
PHOTON_DATA_DIR = os.path.join(DATA_DIR, "photon_data")
TEMP_DIR = os.path.join(DATA_DIR, "temp")
OS_NODE_DIR = os.path.join(PHOTON_DATA_DIR, "node_1")

if FILE_URL:
    UPDATE_STRATEGY = "DISABLED"
    if not MD5_URL:
        SKIP_MD5_CHECK = True
