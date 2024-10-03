#!/bin/bash

# Function to handle errors and exit
handle_error() {
	echo "Error: $1"
	exit 1
}

# Download elasticsearch index
if [ ! -d "/photon/photon_data/elasticsearch" ]; then
	echo "Downloading search index"
	if [[ ! -z "${COUNTRY_CODE}" ]]; then
		wget --progress=dot:giga -O - http://download1.graphhopper.com/public/extracts/by-country-code/${COUNTRY_CODE}/photon-db-${COUNTRY_CODE}-latest.tar.bz2 | bzip2 -cd | tar x || handle_error "Failed to download or extract country-specific Photon DB"
	else
		wget --progress=dot:giga -O - http://download1.graphhopper.com/public/photon-db-latest.tar.bz2 | bzip2 -cd | tar x || handle_error "Failed to download or extract the latest Photon DB"
	fi

	# Check if the download and extraction were successful
	if [ ! -d "/photon/photon_data/elasticsearch" ]; then
		handle_error "Search index directory does not exist after extraction"
	fi
else
	echo "Search index directory already exists"
fi

# Start photon if elastic index exists
if [ -d "/photon/photon_data/elasticsearch" ]; then
	echo "Starting Photon"
	java -jar photon.jar "$@" || handle_error "Failed to start Photon"
else
	handle_error "Could not start Photon, the search index could not be found"
fi
