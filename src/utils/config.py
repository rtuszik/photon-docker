import os

# USER CONFIG
UPDATE_STRATEGY = os.getenv("UPDATE_STRATEGY", "SEQUENTIAL")
UPDATE_INTERVAL = os.getenv("UPDATE_INTERVAL", "30d")
REGION = os.getenv("REGION")
FORCE_UPDATE = os.getenv("FORCE_UPDATE", "False").lower() in ("true", "1", "t")
FILE_URL = os.getenv("FILE_URL")
DOWNLOAD_MAX_RETRIES = os.getenv("DOWNLOAD_MAX_RETRIES", "3")
PHOTON_PARAMS = os.getenv("PHOTON_PARAMS")
JAVA_PARAMS = os.getenv("JAVA_PARAMS")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
BASE_URL = os.getenv("BASE_URL", "https://r2.koalasec.org/public").rstrip("/")
SKIP_MD5_CHECK = os.getenv("SKIP_MD5_CHECK", "False").lower() in ("true", "1", "t")
INITIAL_DOWNLOAD = os.getenv("INITIAL_DOWNLOAD", "True").lower() in ("true", "1", "t")
APPRISE_URLS = os.getenv("APPRISE_URLS")

# APP CONFIG
PHOTON_DIR = "/photon"
DATA_DIR = "/photon/data"
PHOTON_DATA_DIR = os.path.join(DATA_DIR, "photon_data")
TEMP_DIR = os.path.join(DATA_DIR, "temp")
OS_NODE_DIR = os.path.join(PHOTON_DATA_DIR, "node_1")
