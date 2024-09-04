# Photon Docker Image for Privacy and Integration with Dawarich

## Overview

Photon is an open-source geocoding solution built for OpenStreetMap (OSM) data, providing features such as search-as-you-type and reverse geocoding. This repository offers a Docker image for running Photon locally, enhancing data privacy and integration capabilities with services like Dawarich.

### Integration with Dawarich

This setup allows for seamless integration with Dawarich, a service used for tracking and analyzing location data. Running Photon locally enables:

1. **Data Privacy**: Local geocoding operations ensure that location data is not sent to external servers.
2. **Performance Optimization**: Reducing the need for external API calls minimizes latency and improves response times.
3. **Operational Control**: Using Docker containers allows for straightforward management, updates, and scalability of the geocoding service.

## Features

- **Automated Release Monitoring**: Checks for new Photon releases regularly.
- **Automated Docker Image Build**: Builds Docker images for new Photon releases.
- **DockerHub Publishing**: Publishes the built images to DockerHub for easy access.
- **Release Tracking**: Automatically creates a release in this repository for each new Photon version.

## Usage

### Prerequisites

- Docker and Docker Compose must be installed.

### Pull and Run Pre-built Photon Image

```yaml
version: "3.8"

services:
  photon:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        - PHOTON_VERSION=${PHOTON_VERSION}
    ports:
      - "2322:2322"
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

## Contributing

Contributions are welcome. Please submit pull requests or open issues for suggestions and improvements.

## License

This project is licensed under the Apache License, Version 2.0.

## Acknowledgments

- [Photon](https://github.com/komoot/photon): The open-source geocoding solution used in this project.
- [Dawarich](https://github.com/Freika/dawarich): A location tracking service compatible with this setup.
