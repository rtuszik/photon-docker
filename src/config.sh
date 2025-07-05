#!/bin/bash

# Fixed paths
PHOTON_DIR="/photon"
PHOTON_DATA_DIR="${PHOTON_DIR}/photon_data"
PHOTON_JAR="${PHOTON_DIR}/photon.jar"
OS_DATA_DIR="${PHOTON_DATA_DIR}/node_1"
INDEX_DIR="${OS_DATA_DIR}"
ES_DATA_DIR="${PHOTON_DATA_DIR}/elasticsearch"
TEMP_DIR="${PHOTON_DATA_DIR}/temp"
PID_FILE="${PHOTON_DIR}/photon.pid"
FILE_URL="$FILE_URL"
PHOTON_PARAMS="${PHOTON_PARAMS}"
JAVA_PARAMS="${JAVA_PARAMS}"


# Environment variables with defaults
UPDATE_STRATEGY=${UPDATE_STRATEGY:-SEQUENTIAL}
UPDATE_INTERVAL=${UPDATE_INTERVAL:-30d}
LOG_LEVEL=${LOG_LEVEL:-INFO}
BASE_URL=${BASE_URL:-https://r2.koalasec.org/public/experimental}
BASE_URL=${BASE_URL%/}
FORCE_UPDATE=${FORCE_UPDATE:-FALSE}
SKIP_MD5_CHECK=${SKIP_MD5_CHECK:-FALSE}

# Validate UPDATE_STRATEGY
if [[ ! "${UPDATE_STRATEGY}" =~ ^(SEQUENTIAL|PARALLEL|DISABLED)$ ]]; then
    echo "ERROR: Invalid UPDATE_STRATEGY: ${UPDATE_STRATEGY}"
    echo "Valid options are: SEQUENTIAL, PARALLEL, DISABLED"
    exit 1
fi

log_info "Ensuring correct permissions for /photon directory..."
chown -R -v photon:photon /photon
