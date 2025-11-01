![Docker Pulls](https://img.shields.io/docker/pulls/rtuszik/photon-docker) ![Docker Image Size](https://img.shields.io/docker/image-size/rtuszik/photon-docker) ![Docker Image Version](https://img.shields.io/docker/v/rtuszik/photon-docker) ![GitHub Release](https://img.shields.io/github/v/release/komoot/photon?label=Photon) ![Lint Status](https://github.com/rtuszik/photon-docker/actions/workflows/lint.yml/badge.svg)

# Photon Docker Image

## Overview

This is an _unofficial_ docker image for [Photon](https://github.com/komoot/photon)

Photon is an open-source geocoding solution built for OpenStreetMap (OSM) data,
providing features such as search-as-you-type and reverse geocoding.
This repository offers a Docker image for running Photon locally,
enhancing data privacy and integration capabilities with services like [Dawarich](https://github.com/Freika/dawarich).

## Important Notes

⚠️ **Warning: Large File Sizes** ⚠️

- The Photon index file is fairly large and growing steadily.
  As of the beginning of 2025, around 200GB is needed for the full index,
  and it is growing by 10-20GB per year.
- Ensure you have sufficient disk space available before running the container.
- The initial download and extraction process may take a considerable amount of time.
  Depending on your hardware, checksum verification and decompression may take multiple hours.

♻️ **Change in Default Download Source** ♻️

- To reduce the load on the official Photon servers,
  the default `BASE_URL` for downloading the index files now points to a community-hosted mirror.
  Please see the **Community Mirrors** section for more details.

## Usage

### Example Docker Compose

```yaml
services:
    photon:
        image: rtuszik/photon-docker:latest
        environment:
            - UPDATE_STRATEGY=PARALLEL
            - UPDATE_INTERVAL=720h # Check for updates every 30 days
            # - REGION=andorra # Optional: specific region (continent, country, or planet)
            # - APPRISE_URLS=pover://user@token  # Optional: notifications
        volumes:
            - photon_data:/photon/data
        restart: unless-stopped
        ports:
            - "2322:2322"
volumes:
    photon_data:
```

```bash
docker compose up -d
```

### Configuration Options

The container can be configured using the following environment variables:

| Variable               | Parameters                             | Default                          | Description                                                                                                                                                                                                                                                                            |
| ---------------------- | -------------------------------------- | -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `UPDATE_STRATEGY`      | `PARALLEL`, `SEQUENTIAL`, `DISABLED`   | `SEQUENTIAL`                     | Controls how index updates are handled. `PARALLEL` downloads the new index in the background then swaps with minimal downtime (requires 2x space). `SEQUENTIAL` stops Photon, deletes the existing index, downloads the new one, then restarts. `DISABLED` prevents automatic updates. |
| `UPDATE_INTERVAL`      | Time string (e.g., "720h", "30d")      | `30d`                            | How often to check for updates. To reduce server load, it is recommended to set this to a long interval (e.g., `720h` for 30 days) or disable updates altogether if you do not need the latest data.                                                                                   |
| `REGION`               | Region name, country code, or `planet` | `planet`                         | Optional region for a specific dataset. Can be a continent (`europe`, `asia`), individual country/region (`germany`, `usa`, `japan`), country code (`de`, `us`, `jp`), or `planet` for worldwide data. See [Available Regions](#available-regions) section for details.                |
| `LOG_LEVEL`            | `DEBUG`, `INFO`, `ERROR`               | `INFO`                           | Controls logging verbosity.                                                                                                                                                                                                                                                            |
| `FORCE_UPDATE`         | `TRUE`, `FALSE`                        | `FALSE`                          | Forces an index update on container startup, regardless of `UPDATE_STRATEGY`.                                                                                                                                                                                                          |
| `DOWNLOAD_MAX_RETRIES` | Number                                 | `3`                              | Maximum number of retries for failed downloads.                                                                                                                                                                                                                                        |
| `INITIAL_DOWNLOAD`     | `TRUE`, `FALSE`                        | `TRUE`                           | Controls whether the container performs the initial index download when the Photon data directory is empty. Useful for manual imports.                                                                                                                                                 |
| `BASE_URL`             | Valid URL                              | `https://r2.koalasec.org/public` | Custom base URL for index data downloads. Should point to the parent directory of index files. The default has been changed to a community mirror to reduce load on the GraphHopper servers.                                                                                           |
| `SKIP_MD5_CHECK`       | `TRUE`, `FALSE`                        | `FALSE`                          | Optionally skip MD5 verification of downloaded index files.                                                                                                                                                                                                                            |
| `FILE_URL`             | URL to a .tar.bz2 file                 | -                                | Set a custom URL for the index file to be downloaded (e.g., "https://download1.graphhopper.com/public/experimental/photon-db-latest.tar.bz2"). This must be a tar.bz2 format. Make sure to set the `UPDATE_STRATEGY` to `DISABLED` when using this option.                             |
| `PHOTON_PARAMS`        | Photon executable parameters           | -                                | See `https://github.com/komoot/photon#running-photon.`                                                                                                                                                                                                                                 |
| `APPRISE_URLS`         | Comma-separated Apprise URLs           | -                                | Optional notification URLs for [Apprise](https://github.com/caronc/apprise) to send status updates (e.g., download completion, errors). Supports multiple services like Pushover, Slack, email, etc. Example: `pover://user@token,mailto://user:pass@gmail.com`                        |
| `PUID`                 | User ID                                | 9011                             | The User ID for the photon process. Set this to your host user's ID (`id -u`) to prevent permission errors when using bind mounts.                                                                                                                                                     |
| `PGID`                 | Group ID                               | 9011                             | The Group ID for the photon process. Set this to your host group's ID (`id -g`) to prevent permission errors when using bind mounts.                                                                                                                                                   |

## Available Regions

### 1. Planet-wide Data

(This is the default if no region is specified)

- **Region**: `planet`
- **Size**: ~116GB
- **Coverage**: Worldwide

### 2. Continental Data

- **africa** (~2.8GB)
- **asia** (~13.5GB)
- **australia-oceania** (~2.9GB)
- **europe** (~60.7GB)
- **north-america** (~29.5GB)
- **south-america** (~13.8GB)

### 3. Individual Countries/Regions

Only **16 regions** have individual database downloads available:

#### Asia (2 regions)

- **india** (also: `in`)
- **japan** (also: `jp`)

#### Europe (10 regions)

- **andorra** (also: `ad`)
- **austria** (also: `at`)
- **denmark** (also: `dk`)
- **france-monacco** (also: `fr`, `france`, `monaco`)
- **germany** (also: `de`, `deutschland`)
- **luxemburg** (also: `lu`, `luxembourg`)
- **netherlands** (also: `nl`, `holland`, `the netherlands`)
- **russia** (also: `ru`)
- **slovakia** (also: `sk`)
- **spain** (also: `es`, `españa`, `espana`)

#### North America (3 regions)

- **canada** (also: `ca`)
- **mexico** (also: `mx`)
- **usa** (also: `us`, `united states`, `united states of america`)

#### South America (1 region)

- **argentina** (also: `ar`)

### Usage Examples

```yaml
# Continental download
- REGION=europe

# Individual country by name
- REGION=andorra

# Individual country by code
- REGION=de
```

## Community Mirrors

To ensure the sustainability of the Photon project and reduce the load on the official GraphHopper download servers,
this Docker image now defaults to using community-hosted mirrors.

> ⚠️ **Disclaimer:** Community mirrors are not officially managed by the Photon team or the maintainer of this Docker image.
> There are **no guarantees regarding the availability, performance, or integrity of the data** provided by these mirrors. Use them at your own discretion.

If you are hosting a public mirror, please open an issue or pull request to have it added to this list.

| URL                                         | Maintained By                                          | Status                                                                                                                                                                       |
| ------------------------------------------- | ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `https://download1.graphhopper.com/public/` | [GraphHopper](https://www.graphhopper.com/) (Official) | ![GraphHopper](https://img.shields.io/website?url=https%3A%2F%2Fdownload1.graphhopper.com%2Fpublic%2Fphoton-db-planet-0.7OS-latest.tar.bz2&style=for-the-badge&label=Status) |
| `https://r2.koalasec.org/public/`           | [rtuszik](https://github.com/rtuszik)                  | ![KoalaSec](https://img.shields.io/website?url=https%3A%2F%2Fr2.koalasec.org%2Fpublic%2Fphoton-db-planet-0.7OS-latest.tar.bz2&style=for-the-badge&label=Status)              |

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

- Do _not_ set `PHOTON_API_USE_HTTPS` to `true` unless your photon instance is available using HTTPS.
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

<!-- end list -->
