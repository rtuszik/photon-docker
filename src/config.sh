#!/bin/bash

# Fixed paths
PHOTON_DIR="/photon"
PHOTON_DATA_DIR="${PHOTON_DIR}/photon_data"
PHOTON_JAR="${PHOTON_DIR}/photon.jar"
ES_DATA_DIR="${PHOTON_DATA_DIR}/elasticsearch"
INDEX_DIR="${ES_DATA_DIR}"
TEMP_DIR="${PHOTON_DATA_DIR}/temp"
PID_FILE="${PHOTON_DIR}/photon.pid"

# Environment variables with defaults
UPDATE_STRATEGY=${UPDATE_STRATEGY:-SEQUENTIAL}
UPDATE_INTERVAL=${UPDATE_INTERVAL:-24h}
LOG_LEVEL=${LOG_LEVEL:-INFO}
BASE_URL=${BASE_URL:-https://download1.graphhopper.com/public}
FORCE_UPDATE=${FORCE_UPDATE:-FALSE}

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Validate UPDATE_STRATEGY
if [[ ! "${UPDATE_STRATEGY}" =~ ^(SEQUENTIAL|PARALLEL|DISABLED)$ ]]; then
    echo "ERROR: Invalid UPDATE_STRATEGY: ${UPDATE_STRATEGY}"
    echo "Valid options are: SEQUENTIAL, PARALLEL, DISABLED"
    exit 1
fi
