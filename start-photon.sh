#!/bin/bash

# Set the data directory and index URL
DATA_DIR="/photon_data"
# INDEX_URL="http://download1.graphhopper.com/public/photon-db-latest.tar.bz2"
INDEX_URL="https://download1.graphhopper.com/public/extracts/by-country-code/de/photon-db-de-latest.tar.bz2"

# Download elasticsearch index if it doesn't exist
if [ ! -d "${DATA_DIR}/elasticsearch" ]; then
	echo "Downloading search index"
	wget --progress=dot:giga -O - "$INDEX_URL" | pbzip2 -cd | tar x -C "$DATA_DIR"
fi

# Start photon if elastic index exists
if [ -d "${DATA_DIR}/elasticsearch" ]; then
	echo "Starting Photon"
	exec java -jar /photon.jar
else
	echo "Could not start Photon, the search index could not be found"
	exit 1
fi
