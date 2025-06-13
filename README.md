![Docker Pulls](https://img.shields.io/docker/pulls/rtuszik/photon-docker) ![Docker Image Size](https://img.shields.io/docker/image-size/rtuszik/photon-docker) ![Docker Image Version](https://img.shields.io/docker/v/rtuszik/photon-docker) ![GitHub Release](https://img.shields.io/github/v/release/komoot/photon?label=Photon) ![Lint Status](https://github.com/rtuszik/photon-docker/actions/workflows/lint.yml/badge.svg)

# Photon Docker Image

## Overview

This is an _unofficial_ docker image for [Photon](https://github.com/komoot/photon)

Photon is an open-source geocoding solution built for OpenStreetMap (OSM) data, providing features such as search-as-you-type and reverse geocoding.
This repository offers a Docker image for running Photon locally, enhancing data privacy and integration capabilities with services like [Dawarich](https://github.com/Freika/dawarich).

## Important Notes

⚠️ **Warning: Large File Sizes** ⚠️

- The Photon index file is fairly large and growing steadily. As of beginning of 2025, around 200GB is needed for the full index. Growing 10-20GB per year.
- Ensure you have sufficient disk space available before running the container.
- The initial download and extraction process may take a considerable amount of time. Depending on your hardware, checksum verification and decompression may take multiple hours.

## Usage

### Configuration Options

The container can be configured using the following environment variables:

| Variable          | Parameters                                | Default                                    | Description                                                                                                                                                                                                                                                            |
| ----------------- | ----------------------------------------- | ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `UPDATE_STRATEGY` | `PARALLEL`, `SEQUENTIAL`, `DISABLED`      | `SEQUENTIAL`                               | Controls how index updates are handled. `PARALLEL` downloads new index in background then swaps with minimal downtime (requires 2x space). `SEQUENTIAL` stops Photon, deletes existing index, downloads new one, then restarts. `DISABLED` prevents automatic updates. |
| `UPDATE_INTERVAL` | Time string (e.g., "24h", "60m", "3600s") | `24h`                                      | How often to check for updates                                                                                                                                                                                                                                         |
| `COUNTRY_CODE`    | Two-letter country code                   | -                                          | Optional country code for smaller index ([available codes](https://download1.graphhopper.com/public/extracts/by-country-code/)). Only one country code is supported at a time.                                                                                         |
| `LOG_LEVEL`       | `DEBUG`, `INFO`, `ERROR`                  | `INFO`                                     | Controls logging verbosity                                                                                                                                                                                                                                             |
| `FORCE_UPDATE`    | `TRUE`, `FALSE`                           | `FALSE`                                    | Forces index update on container startup, regardless of UPDATE_STRATEGY                                                                                                                                                                                                |
| `BASE_URL`        | Valid URL                                 | `https://download1.graphhopper.com/public` | Custom base URL for index data downloads. Should point to parent directory of index files.                                                                                                                                                                             |
| `SKIP_MD5_CHECK`  | `TRUE`, `FALSE`                           | `FALSE`                                    | Optionally skip MD5 verification of downloaded index files                                                                                                                                                                                                             |
| `FILE_URL`        | URL to a .tar.bz2 file                    | -                                          | Set custom URL for index file to be downloaded (e.g., "https://download1.graphhopper.com/public/experimental/photon-db-latest.tar.bz2"). Needs to be tar.bz2 format. Make sure to set the UPDATE_STRATEGY to DISABLED when using this option.                          |

### Example Docker Compose

```yaml
services:
    photon:
        image: rtuszik/photon-docker:latest
        environment:
            - UPDATE_STRATEGY=PARALLEL
            - UPDATE_INTERVAL=24h
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

- Do _not_ set PHOTON_API_USE_HTTPS to true unless your photon instance is available using HTTPS.
- Only use the host address for your photon instance. Do not append `/api`

### Build and Run Locally

    ```bash
    docker compose -f docker-compose.build.yml build --build-arg PHOTON_VERSION=0.6.2
    ```

### Accessing the API

The Photon API is available at:

```
http://localhost:2322/api?q=Harare
```

## Contributing

Contributions are welcome. Please submit pull requests or open issues for suggestions and improvements.

## License

This project is licensed under the Apache License, Version 2.0.

## Acknowledgments

- [Photon](https://github.com/komoot/photon)
- [Dawarich](https://github.com/Freika/dawarich)
