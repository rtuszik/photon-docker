![Docker Pulls](https://img.shields.io/docker/pulls/rtuszik/photon-docker) ![Docker Image Size](https://img.shields.io/docker/image-size/rtuszik/photon-docker) ![Docker Image Version](https://img.shields.io/docker/v/rtuszik/photon-docker) ![GitHub Release](https://img.shields.io/github/v/release/komoot/photon?label=Photon)

# Photon Docker Image

## Overview

This is an _unofficial_ docker image for [Photon](https://github.com/komoot/photon)

Photon is an open-source geocoding solution built for OpenStreetMap (OSM) data, providing features such as search-as-you-type and reverse geocoding.
This repository offers a Docker image for running Photon locally, enhancing data privacy and integration capabilities with services like [Dawarich](https://github.com/Freika/dawarich).

Running Photon locally enables:

1. **Data Privacy**: Local geocoding operations ensure that location data is not sent to external servers.
2. **Performance Optimization**: Reducing the need for external API calls minimizes latency and improves response times.
3. **Operational Control**: Using Docker containers allows for straightforward management, updates, and scalability of the geocoding service.

## Important Notes

⚠️ **Warning: Large File Sizes** ⚠️

-   The Photon index file is fairly large (approximately 75-76GB compressed, 150-160GB uncompressed).
-   Ensure you have sufficient disk space available before running the container.
-   The initial download and extraction process may take a considerable amount of time.

## Usage

-   If you want to download only a single country, you may specify the country code using the "COUNTRY_CODE" variable in docker compose.
-   You can find a list of available country codes [here](https://download1.graphhopper.com/public/extracts/by-country-code/)

```yaml
services:
    photon:
        image: rtuszik/photon-docker:latest
        environment:
            - COUNTRY_CODE=zw
            - LOG_LEVEL=INFO # Options: DEBUG, INFO, ERROR
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

### Build and Run Photon Image Locally

1. Set the `PHOTON_VERSION` environment variable to the desired version:

    ```bash
    export PHOTON_VERSION=0.5.0
    ```

2. Use Docker Compose to build the image locally and start Photon:

    ```bash
    docker-compose -f docker-compose.build.yml up --build
    ```

    This will build and run Photon using the specified version.

### Accessing Photon

-   The Photon API can be accessed at:

    ```
    http://localhost:2322/api?q=Harare
    ```

    Replace `Harare` with any other query as needed.

## Data Persistence

The Photon index is stored in a Docker volume (`photon_data`) to persist the data across container restarts and removals. This also allows you to pre-populate the volume with an existing index if needed.

## Initial Download and Updates

-   On first run, the container will download and extract the latest Photon index, which may take several hours depending on your internet connection and system performance.

## Contributing

Contributions are welcome. Please submit pull requests or open issues for suggestions and improvements.

## License

This project is licensed under the Apache License, Version 2.0.

## Acknowledgments

-   [Photon](https://github.com/komoot/photon)
-   [Dawarich](https://github.com/Freika/dawarich)
