![Docker Pulls](https://img.shields.io/docker/pulls/rtuszik/photon-docker) ![Docker Image Size](https://img.shields.io/docker/image-size/rtuszik/photon-docker) ![Docker Image Version](https://img.shields.io/docker/v/rtuszik/photon-docker) ![GitHub Release](https://img.shields.io/github/v/release/komoot/photon?label=Photon) ![Lint Status](https://github.com/rtuszik/photon-docker/actions/workflows/lint.yml/badge.svg)

# Photon Docker Image

## Overview

_Unofficial_ docker image for [Photon](https://github.com/komoot/photon)

Photon is an open-source geocoding solution built for OpenStreetMap (OSM) data, providing features such as search-as-you-type and reverse geocoding.
This repository offers a Docker image for running Photon locally, enhancing data privacy and integration capabilities with services like [Dawarich](https://github.com/Freika/dawarich).

## Important Notes

⚠️ **Warning: Large File Sizes** ⚠️

-   The Photon index file is fairly large (approximately 75-76GB compressed, 150-160GB uncompressed).
-   Ensure you have sufficient disk space available before running the container.
-   The initial download and extraction process may take a considerable amount of time.

## Usage

### Configuration Options

The container can be configured using the following environment variables:

-   `UPDATE_STRATEGY`: Controls how index updates are handled
    -   `PARALLEL`: Downloads new index in background, then swaps with minimal downtime, requires 2x index space (Default)
    -   `SEQUENTIAL`: Stops Photon, deletes the existing index files, downloads the new index, then restarts
    -   `DISABLED`: No automatic updates
-   `UPDATE_INTERVAL`: How often to check for updates (e.g., "24h", "60m", "3600s")
-   `LOG_LEVEL`: Logging verbosity ("DEBUG", "INFO", "ERROR")
-   `FORCE_UPDATE`: Forces an index update on container startup, regardless of UPDATE_STRATEGY setting ("TRUE", "FALSE")
-   `COUNTRY_CODE`: Optional country code for smaller index (see [available codes](https://download1.graphhopper.com/public/extracts/by-country-code/))
    Please note, that you may only specify a single country code. Specifying multiple country codes will make the script default to the full planet index.
    This is a limitation with the public data dumps provided by graphhopper.

### Example Docker Compose

```yaml
services:
    photon:
        image: rtuszik/photon-docker:latest
        environment:
            - UPDATE_STRATEGY=SEQUENTIAL
            - UPDATE_INTERVAL=24h
            - LOG_LEVEL=INFO
            # - FORCE_UPDATE=TRUE  # Optional: force index update on startup
            # - COUNTRY_CODE=zw  # Optional: country-specific index
        volumes:
            - photon_data:/photon/photon_data
        restart: unless-stopped
        ports:
            - "2322:2322"
volumes:
    photon_data:
```

```bash
docker-compose up -d
```

### Use with Dawarich

This docker container for photon can be used as your reverse-geocoder for the [Dawarich Location History Tracker](https://github.com/Freika/dawarich)

To connect dawarich to your photon instance, the following environment variables need to be set in your dawarich docker-compose.yml:

```yaml
PHOTON_API_HOST={PHOTON-IP}:{PORT}
PHOTON_API_USE_HTTPS=false
```

for example:

```yaml
PHOTON_API_HOST=192.168.10.10:2322
PHOTON_API_USE_HTTPS=false
```

-   Do _not_ set PHOTON_API_USE_HTTPS to true unless your photon instance is available using HTTPS.
-   Only use the host address for your photon instance. Do not append `/api`

### Accessing the API

The Photon API is available at:

```
http://localhost:2322/api?q=Harare
```

## Data Management

### Index Updates

-   The container automatically checks for newer index versions
-   Updates respect a 1-hour tolerance to prevent unnecessary downloads
-   Progress and status are logged based on LOG_LEVEL setting

### Data Persistence

-   Indexes are stored in the `photon_data` Docker volume
-   Data persists across container restarts
-   Initial download occurs only if no valid index exists

### Storage Requirements

-   Full index: ~80GB compressed, ~up to 200GB uncompressed (Entire Planet)
-   Country-specific indexes are significantly smaller
-   Ensure sufficient disk space before deployment

## Contributing

Contributions are welcome. Please submit pull requests or open issues for suggestions and improvements.

## License

This project is licensed under the Apache License, Version 2.0.

## Acknowledgments

-   [Photon](https://github.com/komoot/photon)
-   [Dawarich](https://github.com/Freika/dawarich)
