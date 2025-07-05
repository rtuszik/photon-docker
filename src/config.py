import os

# USER CONFIG
UPDATE_STRATEGY = os.getenv("UPDATE_STRATEGY", "SEQUENTIAL")
FORCE_UPDATE = os.getenv("FORCE_UPDATE", 'False').lower() in ('true', '1', 't')
FILE_URL=os.getenv("FILE_URL")
PHOTON_PARAMS=os.getenv("PHOTON_PARAMS")
JAVA_PARAMS=os.getenv("JAVA_PARAMS")
LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO")
COUNTRY_CODE=os.getenv("COUNTRY_CODE")

# APP CONFIG
PHOTON_DIR =  "/photon"
PHOTON_DATA_DIR = PHOTON_DIR + "/photon_data"
TEMP_DIR = PHOTON_DIR + "/temp"

OS_NODE_DIR = PHOTON_DATA_DIR + "/node_1"

PID_FILE= PHOTON_DIR + "/photon.pid"
