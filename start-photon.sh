#!/bin/bash

set -eo pipefail

DATA_DIR="/photon_data"
TEMP_DIR="/tmp/photon_update"
INDEX_URL="http://download1.graphhopper.com/public/extracts/by-country-code/nl/photon-db-nl-latest.tar.bz2"
# INDEX_URL="https://download1.graphhopper.com/public/photon-db-latest.tar.bz2"
# wget --user-agent="$USER_AGENT" -O - http://download1.graphhopper.com/public/extracts/by-country-code/nl/photon-db-nl-latest.tar.bz2 | bzip2 -cd | tar x
VERSION_FILE="${DATA_DIR}/version.txt"

# Function to download and extract the index
download_and_extract_index() {
	echo "Downloading and extracting Photon index..."
	mkdir -p "$TEMP_DIR"
	wget -O - "$INDEX_URL" | pbzip2 -cd | tar x -C "$TEMP_DIR"

	# Remove old data and move new data into place
	rm -rf "${DATA_DIR:?}/*"
	mv "$TEMP_DIR"/* "$DATA_DIR/"
	rm -rf "$TEMP_DIR"

	date +%Y%m%d >"$VERSION_FILE"
	echo "Index downloaded, extracted, and moved successfully."
}

# Check if we need to download the index
if [ ! -d "${DATA_DIR}/elasticsearch" ] || [ -z "$(ls -A ${DATA_DIR}/elasticsearch)" ] || [ "$UPDATE_INDEX" = "true" ]; then
	echo "Downloading index due to missing data or UPDATE_INDEX flag..."
	download_and_extract_index
else
	echo "Using existing data in ${DATA_DIR}/elasticsearch"
fi

# Start Photon
echo "Starting Photon..."
exec java -jar /photon.jar
