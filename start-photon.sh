#!/bin/bash

set -e

DATA_DIR="/app/photon_data"
INDEX_URL="https://download1.graphhopper.com/public/photon-db-latest.tar.bz2"

# Function to download and extract the index
download_and_extract_index() {
	echo "Downloading and extracting the Photon index..."
	mkdir -p "$DATA_DIR"
	wget -O - "$INDEX_URL" | pbzip2 -cd | tar x -C "$DATA_DIR"
	echo "Index downloaded and extracted successfully."
}

# Check if the index already exists
if [ ! -d "$DATA_DIR" ] || [ -z "$(ls -A "$DATA_DIR")" ]; then
	download_and_extract_index
else
	echo "Photon index already exists. Skipping download."
fi

# Start Photon
echo "Starting Photon..."
exec java -jar photon.jar -data-dir "$DATA_DIR"
