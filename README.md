# Photon Docker Image

## Overview

Photon is an open-source geocoding solution built for OpenStreetMap (OSM) data, providing features such as search-as-you-type and reverse geocoding. This repository offers a Docker image for running Photon locally, enhancing data privacy and integration capabilities with services like Dawarich.

Running Photon locally enables:

1. **Data Privacy**: Local geocoding operations ensure that location data is not sent to external servers.
2. **Performance Optimization**: Reducing the need for external API calls minimizes latency and improves response times.
3. **Operational Control**: Using Docker containers allows for straightforward management, updates, and scalability of the geocoding service.

## Features

- **Automated Release Monitoring**: Checks for new Photon releases regularly.
- **Automated Docker Image Build**: Builds Docker images for new Photon releases.
- **DockerHub Publishing**: Publishes the built images to DockerHub for easy access.
- **Release Tracking**: Automatically creates a release in this repository for each new Photon version.
- **Auto-Update**: By default, the container checks for and downloads updates to the Photon index.

## Important Notes

⚠️ **Warning: Large File Sizes** ⚠️

- The Photon index file is extremely large (approximately 75-76GB compressed, 150-160GB uncompressed).
- Ensure you have sufficient disk space available before running the container.
- The initial download and extraction process may take a considerable amount of time.

## Usage

### Prerequisites

- Docker and Docker Compose must be installed.
- At least 160GB of free disk space for the Photon index and temporary files during updates.

### Pull and Run Pre-built Photon Image

```yaml
version: "3"

services:
  photon:
    image: rtuszik/photon-docker:latest
    ports:
      - "2322:2322"
    volumes:
      - photon_data:/app/photon_data
    environment:
      - AUTO_UPDATE_INDEX=true # Set to false to disable automatic updates

volumes:
  photon_data:
```

```bash
docker-compose up -d
```

### Build and Run Photon Image Locally

1. Set the `PHOTON_VERSION` environment variable to the desired version:

   ```bash
   export PHOTON_VERSION=0.4.0
   ```

2. Use Docker Compose to build the image locally and start Photon:

   ```bash
   docker-compose -f docker-compose.build.yml up --build
   ```

   This will build and run Photon using the specified version.

### Accessing Photon

- The Photon API can be accessed at:

  ```
  http://localhost:2322/api?q=berlin
  ```

  Replace `berlin` with any other query as needed.

## Configuration Options

- `AUTO_UPDATE_INDEX`: Set to `false` to disable automatic updates of the Photon index. Default is `true`.
  ```yaml
  environment:
    - AUTO_UPDATE_INDEX=false
  ```

## Data Persistence

The Photon index is stored in a Docker volume (`photon_data`) to persist the data across container restarts and removals. This also allows you to pre-populate the volume with an existing index if needed.

## Initial Download and Updates

- On first run, the container will download and extract the latest Photon index, which may take several hours depending on your internet connection and system performance.
- By default, the container checks for updates to the index weekly. This behavior can be disabled by setting `AUTO_UPDATE_INDEX=false`.
- Even with auto-updates disabled, the container will perform the initial download if the data directory is empty.

## Contributing

Contributions are welcome. Please submit pull requests or open issues for suggestions and improvements.

## License

This project is licensed under the Apache License, Version 2.0.

## Acknowledgments

- [Photon](https://github.com/komoot/photon): The open-source geocoding solution used in this project.
- [Dawarich](https://github.com/Freika/dawarich): A location tracking service compatible with this setup.
