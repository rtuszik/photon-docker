#!/bin/bash

# Download elasticsearch index
if [ ! -d "/photon/photon_data/elasticsearch" ]; then
	echo "Downloading search index"
	if [[ -n "${COUNTRY_CODE}" ]]; then
		wget --progress=dot:giga -O - http://download1.graphhopper.com/public/extracts/by-country-code/${COUNTRY_CODE}/photon-db-${COUNTRY_CODE}-latest.tar.bz2 | pbzip2 -cd | tar x
	else
		wget --progress=dot:giga -O - http://download1.graphhopper.com/public/photon-db-latest.tar.bz2 | pbzip2 -cd | tar x
	fi
fi

# Start photon if elastic index exists
if [ -d "/photon/photon_data/elasticsearch" ]; then
	echo "Start photon"
	java -jar photon.jar $@
else
	echo "Could not start photon, the search index could not be found"
fi
