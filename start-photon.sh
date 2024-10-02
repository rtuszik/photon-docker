#!/bin/bash

set -eo pipefail

DATA_DIR="/app/photon_data"
TEMP_DIR="/tmp/photon_update"
INDEX_URL="https://download1.graphhopper.com/public/"
VERSION_FILE="$DATA_DIR/index_version.txt"
MAX_RETRIES=3
RETRY_DELAY=60

AUTO_UPDATE_INDEX=${AUTO_UPDATE_INDEX:-false}

get_latest_version() {
	local latest_version=$(curl -s "$INDEX_URL" | grep -oP 'photon-db-\d{6}\.tar\.bz2' | sort -r | head -n 1)
	echo "${latest_version%.tar.bz2}"
}

# Function to download and extract the index
download_and_extract_index() {
	local version=$1
	echo "Downloading and extracting Photon index version $version..."
	mkdir -p "$TEMP_DIR"

	for attempt in $(seq 1 $MAX_RETRIES); do
		echo "Download attempt $attempt of $MAX_RETRIES"
		if wget -O - "${INDEX_URL}${version}.tar.bz2" | pbzip2 -cd | tar x -C "$TEMP_DIR"; then
			echo "Index downloaded and extracted successfully."

			# Remove old data and move new data into place
			rm -rf "$DATA_DIR"
			mv "$TEMP_DIR" "$DATA_DIR"

			echo "$version" >"$VERSION_FILE"
			return 0
		else
			echo "Download attempt $attempt failed."
			if [ $attempt -lt $MAX_RETRIES ]; then
				echo "Retrying in $RETRY_DELAY seconds..."
				sleep $RETRY_DELAY
			else
				echo "All download attempts failed."
				rm -rf "$TEMP_DIR"
				return 1
			fi
		fi
	done
}

# Function to check if an update is needed
check_for_updates() {
	local latest_version=$(get_latest_version)
	if [ ! -f "$VERSION_FILE" ]; then
		echo "$latest_version"
		return
	fi
	local current_version=$(cat "$VERSION_FILE")
	if [ "$current_version" != "$latest_version" ]; then
		echo "$latest_version"
	fi
}

# Ensure the data directory exists
mkdir -p "$DATA_DIR"

# Check if the data directory is empty
if [ -z "$(ls -A "$DATA_DIR")" ]; then
	echo "Data directory is empty. Downloading initial index..."
	update_version=$(get_latest_version)
	if ! download_and_extract_index "$update_version"; then
		echo "Failed to download and extract the initial index. Cannot start the service."
		exit 1
	fi
elif [ "$AUTO_UPDATE_INDEX" = true ]; then
	update_version=$(check_for_updates)
	if [ -n "$update_version" ]; then
		if ! download_and_extract_index "$update_version"; then
			echo "Failed to download and extract the index update. Using existing data."
		fi
	else
		echo "Photon index is up-to-date. Skipping download."
	fi
else
	echo "Auto-update is disabled. Using existing data."
fi

# Verify that we have data to work with
if [ -z "$(ls -A "$DATA_DIR")" ]; then
	echo "Error: No data available for Photon. Cannot start the service."
	exit 1
fi

# Start Photon
echo "Starting Photon..."
exec java -jar photon.jar
