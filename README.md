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

- The Photon index is quite large and growing steadily.
  As of mid-2026, the compressed planet index is around 60GB in `db` mode, the planet JSONL dump is around 26GB in `jsonl` mode. These will grow over time.
- Ensure you have sufficient disk space available before running the container.
- The initial download and extraction process may take a considerable amount of time.
  Depending on your hardware, checksum verification and decompression may take multiple hours.

- The JSONL import _will_ take a significant amount of time.
  As a point of reference, a full planet import, tested on a fresh VPS (4C/16GB) took 10 hours and 25 minutes.

- To reduce the load on the official Photon servers,
  the default `BASE_URL` for downloading the index files points to a mirror hosted by my.
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

| Variable               | Parameters                             | Default                          | Description                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ---------------------- | -------------------------------------- | -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `IMPORT_MODE`          | `db`, `jsonl`                          | `db`                             | Selects how the index is built. `db` downloads a prebuilt index for a single region. `jsonl` (**experimental**) builds the index in-container from OpenStreetMap JSONL dumps and supports combining multiple regions. See [Import Modes](#import-modes).                                                                                                                                                                      |
| `UPDATE_STRATEGY`      | `PARALLEL`, `SEQUENTIAL`, `DISABLED`   | `SEQUENTIAL`                     | Controls how index updates are handled. `PARALLEL` downloads the new index in the background then swaps with minimal downtime (requires 2x space). `SEQUENTIAL` stops Photon, deletes the existing index, downloads the new one, then restarts. `DISABLED` prevents automatic updates. Only applies in `db` mode.                                                                                                             |
| `UPDATE_INTERVAL`      | Time string (e.g., "720h", "30d")      | `30d`                            | Minimum age of the local index before checking the mirror for a newer version. Once reached, the mirror is checked at most once per hour until a newer index is available. The age persists across container restarts. To reduce server load, set this to a long interval (e.g., `720h` for 30 days) or disable updates altogether if you do not need the latest data. |
| `REGION`               | Region name, country code, or `planet` | `planet`                         | Region for a specific dataset. Can be a continent (`europe`, `asia`), individual country/region (`germany`, `usa`, `japan`), country code (`de`, `us`, `jp`), or `planet` for worldwide data. In `db` mode exactly one region may be set, and it must be one with a prebuilt index. In `jsonl` mode you may pass multiple regions as a comma-separated list. See [Available Regions](#available-regions) section for details. |
| `LANGUAGES`            | Comma-separated language codes         | -                                | Only used in `jsonl` mode. Languages to import, passed to Photon's `-languages` (e.g. `en,de,fr`).                                                                                                                                                                                                                                                                                                                            |
| `EXTRA_TAGS`           | Comma-separated OSM tags               | -                                | Only used in `jsonl` mode. Additional OSM tags to import, passed to Photon's `-extra-tags`.                                                                                                                                                                                                                                                                                                                                   |
| `IMPORT_GEOMETRIES`    | `TRUE`, `FALSE`                        | `FALSE`                          | Only used in `jsonl` mode. When `TRUE`, imports full geometries (`-full-geometries`) instead of centroids.                                                                                                                                                                                                                                                                                                                    |
| `REVERSE_ONLY`         | `TRUE`, `FALSE`                        | `FALSE`                          | Only used in `jsonl` mode. When `TRUE`, builds a reverse-geocoding-only index (`-reverse-only`), saving roughly 60% of disk space and import time. The forward search endpoints (`/api`, `/structured`) and `/metrics` are disabled on the resulting index; only `/reverse` is served.                                                                                                                                          |
| `LOG_LEVEL`            | `DEBUG`, `INFO`, `ERROR`               | `INFO`                           | Controls logging verbosity.                                                                                                                                                                                                                                                                                                                                                                                                   |
| `PHOTON_LISTEN_IP`     | IP Address                             | 0.0.0.0                          | Populates `-listen-ip` parameter for photon                                                                                                                                                                                                                                                                                                                                                                                   |
| `FORCE_UPDATE`         | `TRUE`, `FALSE`                        | `FALSE`                          | Forces an index update on container startup, regardless of `UPDATE_STRATEGY`.                                                                                                                                                                                                                                                                                                                                                 |
| `DOWNLOAD_MAX_RETRIES` | Number                                 | `3`                              | Maximum number of retries for failed downloads.                                                                                                                                                                                                                                                                                                                                                                               |
| `CHECKSUM_MAX_RETRIES` | Number                                 | `3`                              | Maximum number of download attempts when the MD5 checksum of the downloaded index does not match. A corrupted download is re-fetched up to this many times before the update fails. Ignored when `SKIP_MD5_CHECK` is enabled.                                                                                                                                                                                                 |
| `INITIAL_DOWNLOAD`     | `TRUE`, `FALSE`                        | `TRUE`                           | Controls whether the container performs the initial index download when the Photon data directory is empty. Useful for manual imports.                                                                                                                                                                                                                                                                                        |
| `BASE_URL`             | Valid URL                              | `https://r2.koalasec.org/public` | Custom base URL for index data downloads. Should point to the parent directory of index files. The default has been changed to a community mirror to reduce load on the GraphHopper servers.                                                                                                                                                                                                                                  |
| `SKIP_MD5_CHECK`       | `TRUE`, `FALSE`                        | `FALSE`                          | Optionally skip MD5 verification of downloaded index files.                                                                                                                                                                                                                                                                                                                                                                   |
| `SKIP_SPACE_CHECK`     | `TRUE`, `FALSE`                        | `FALSE`                          | Skip disk space verification before downloading.                                                                                                                                                                                                                                                                                                                                                                              |
| `FILE_URL`             | URL to a .tar.bz2 file                 | -                                | Set a custom URL for the index file to be downloaded (e.g., "https://download1.graphhopper.com/public/experimental/photon-db-latest.tar.bz2"). This must be a tar.bz2 format. Setting this overrides `UPDATE_STRATEGY` to `DISABLED`, and `SKIP_MD5_CHECK` to true if `MD5_URL` is not set.                                                                                                                                   |
| `MD5_URL`              | URL to the MD5 file to use             | -                                | Set a custom URL for the md5 file to be downloaded (e.g., "https://download1.graphhopper.com/public/experimental/photon-db-latest.tar.bz2.md5").                                                                                                                                                                                                                                                                              |
| `PHOTON_PARAMS`        | Photon executable parameters           | -                                | See `https://github.com/komoot/photon#running-photon.`                                                                                                                                                                                                                                                                                                                                                                        |
| `JAVA_PARAMS`          | Java parameters                        | -                                | Extra parameters passed to the `java` command that runs Photon (e.g. heap settings like `-Xmx4g`).                                                                                                                                                                                                                                                                                                                            |
| `APPRISE_URLS`         | Comma-separated Apprise URLs           | -                                | Optional notification URLs for [Apprise](https://github.com/caronc/apprise) to send status updates (e.g., download completion, errors). Supports multiple services like Pushover, Slack, email, etc. Example: `pover://user@token,mailto://user:pass@gmail.com`                                                                                                                                                               |
| `PUID`                 | User ID                                | 9011                             | The User ID for the photon process. Set this to your host user's ID (`id -u`) to prevent permission errors when using bind mounts.                                                                                                                                                                                                                                                                                            |
| `PGID`                 | Group ID                               | 9011                             | The Group ID for the photon process. Set this to your host group's ID (`id -g`) to prevent permission errors when using bind mounts.                                                                                                                                                                                                                                                                                          |
| `ENABLE_METRICS`       | `TRUE`, `FALSE`                        | `FALSE`                          | Enables Prometheus Metrics endpoint at /metrics                                                                                                                                                                                                                                                                                                                                                                               |

## Import Modes

The image can build its search index in two ways, selected with `IMPORT_MODE`:

- **`db` (default):** Downloads a prebuilt index (`.tar.bz2`) for a single region. This is the original behaviour and supports scheduled updates via `UPDATE_STRATEGY` / `UPDATE_INTERVAL`.
- **`jsonl` (experimental):** Builds the index inside the container from compressed OpenStreetMap JSONL dumps. Supports combining multiple regions and tuning the import with `LANGUAGES`, `EXTRA_TAGS`, `IMPORT_GEOMETRIES`, and `REVERSE_ONLY`.

### JSONL Import Mode (Experimental)

> ⚠️ **Experimental:** `jsonl` mode is new and still being stabilised. Its behaviour and configuration may change in future releases, and it is not yet recommended for production use. For stable deployments, use the default `db` mode.

Set `IMPORT_MODE=jsonl` and list one or more regions in `REGION` (comma-separated). The dump is streamed and decompressed directly into Photon's importer, so no decompressed copy is written to disk.

```yaml
services:
    photon:
        image: rtuszik/photon-docker:latest
        environment:
            - IMPORT_MODE=jsonl
            - REGION=germany,austria,switzerland-liechtenstein
            - LANGUAGES=en,de
            # - EXTRA_TAGS=surface,smoothness  # Optional
            # - IMPORT_GEOMETRIES=true         # Optional: full geometries
        volumes:
            - photon_data:/photon/data
        restart: unless-stopped
        ports:
            - "2322:2322"
volumes:
    photon_data:
```

When multiple regions are requested, the smallest dump that covers all of them (a continent, or `planet`) is downloaded, then filtered down to the requested countries.

To build a reverse-geocoding-only index (useful for address lookups from coordinates, e.g. with [Dawarich](https://github.com/Freika/dawarich)), set `REVERSE_ONLY=TRUE`. This produces a much smaller index and faster import, but only the `/reverse` endpoint is served, the forward search endpoints (`/api`, `/structured`) and `/metrics` are disabled.

> ⚠️ **Note:** `jsonl` mode does not currently support scheduled or automatic updates. `UPDATE_STRATEGY` and `UPDATE_INTERVAL` are ignored, and the index is built once at startup. To rebuild, set `FORCE_UPDATE=TRUE` or recreate the data volume. `FILE_URL` and `MD5_URL` are not supported in this mode.

## Available Regions

Region availability depends on `IMPORT_MODE`. **All** regions listed below are available as JSONL dumps (`jsonl` mode). Only a subset have a prebuilt **DB** index, these are the only valid `REGION` values when `IMPORT_MODE=db`.

### 1. Planet-wide Data

(This is the default if no region is specified)

- **Region**: `planet`
- **Availability**: DB and JSONL
- **Size**: ~61GB compressed (DB), ~26GB compressed (JSONL)
- **Coverage**: Worldwide

### 2. Continental Data

Available in both DB and JSONL modes. The sizes below are approximate older estimates and may not reflect current dump sizes.

- **africa** (~2.8GB)
- **asia** (~13.5GB)
- **australia-oceania** (~2.9GB)
- **europe** (~60.7GB)
- **north-america** (~29.5GB)
- **south-america** (~13.8GB)

### 3. Individual Countries/Regions (DB and JSONL)

Only **16 regions** have a prebuilt **DB** index. They are also available as JSONL dumps:

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

### 4. JSONL-only Individual Regions (Experimental)

These regions are available **only** as JSONL dumps (experimental `jsonl` mode); they have no prebuilt DB index. All are sub-regions of Europe. Two-letter country-code aliases work where defined (e.g. `pl`, `se`, `ch`).

- **albania** (`al`), **baltics** (`ee`/`lt`/`lv`), **belarus** (`by`), **belgium** (`be`), **bosnia-herzegovina** (`ba`), **british-islands** (also: `uk`, `great britain`), **bulgaria** (`bg`), **croatia** (`hr`), **cyprus** (`cy`), **czech-republic** (`cz`, `czechia`), **finland** (`fi`), **georgia** (`ge`), **greece** (`gr`), **hungary** (`hu`), **iceland-faroe** (`is`), **ireland** (`ie`), **italy** (`it`), **kosovo** (`xk`), **macedonia** (`mk`), **malta** (`mt`), **moldova** (`md`), **montenegro** (`me`), **norway** (`no`), **poland** (`pl`), **portugal** (`pt`), **romania** (`ro`), **serbia** (`rs`), **slovenia** (`si`), **sweden** (`se`), **switzerland-liechtenstein** (`ch`), **turkey** (`tr`), **ukraine** (`ua`)

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

## Metrics

When `ENABLE_METRICS` is set to `TRUE`, Prometheus metrics are exposed at the `/metrics` endpoint.

An example Grafana Dashboard is available here at [Grafana Labs](https://grafana.com/grafana/dashboards/24901-photon/).

To see a live preview, [visit the public dashboard](https://r10k.grafana.net/public-dashboards/089de1d08d954a959e3a475af8968e1e) of the photon instance hosted by [rtuszik](https://github.com/rtuszik).

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
docker compose -f docker-compose.build.yml build --build-arg PHOTON_VERSION=1.2.0
```

### Accessing the API

The Photon API is available at:

```
http://localhost:2322/api?q=Harare
```

## Contributing

Contributions are welcome.
Please checkout the [Contribution Guidelines](CONTRIBUTING.md).

## License

This project is licensed under the Apache License, Version 2.0.

## Acknowledgments

- [Photon](https://github.com/komoot/photon)
- [Dawarich](https://github.com/Freika/dawarich)

<!-- end list -->
