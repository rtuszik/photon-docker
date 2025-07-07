#!/bin/sh
# This script prepares and runs the photon java application.

JAVA_PARAMS=${JAVA_PARAMS:-""}
PHOTON_PARAMS=${PHOTON_PARAMS:-""}

echo "Starting Photon with:"
echo "JAVA_PARAMS: ${JAVA_PARAMS}"
echo "PHOTON_PARAMS: ${PHOTON_PARAMS}"

eval "exec java ${JAVA_PARAMS} -jar /photon/photon.jar ${PHOTON_PARAMS}"
