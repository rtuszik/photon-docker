FROM eclipse-temurin:21.0.10_7-jre-noble

# install astral uv
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/

ARG DEBIAN_FRONTEND=noninteractive
ARG PHOTON_VERSION
ARG PUID=9011
ARG PGID=9011

RUN apt-get update \
  && apt-get -y install --no-install-recommends \
  lbzip2 \
  gosu \
  python3.12 \
  curl \
  && rm -rf /var/lib/apt/lists/*

RUN groupadd -g ${PGID} -o photon && \
    useradd -l -u ${PUID} -g photon -o -s /bin/false -m -d /photon photon

WORKDIR /photon

RUN mkdir -p /photon/data/

ADD https://github.com/komoot/photon/releases/download/${PHOTON_VERSION}/photon-opensearch-${PHOTON_VERSION}.jar /photon/photon.jar

COPY src/ ./src/
COPY entrypoint.sh .
COPY pyproject.toml .
COPY uv.lock .
RUN gosu photon uv sync --locked


RUN chmod 644 /photon/photon.jar && \
    chown -R photon:photon /photon

LABEL org.opencontainers.image.title="photon-docker" \
      org.opencontainers.image.description="Unofficial docker image for the Photon Geocoder" \
      org.opencontainers.image.url="https://github.com/rtuszik/photon-docker" \
      org.opencontainers.image.source="https://github.com/rtuszik/photon-docker" \
      org.opencontainers.image.documentation="https://github.com/rtuszik/photon-docker#readme"

EXPOSE 2322

HEALTHCHECK --interval=30s --timeout=10s --start-period=240s --retries=3 \
  CMD curl -f http://localhost:2322/status || exit 1

ENTRYPOINT ["/bin/sh", "entrypoint.sh"]
CMD ["uv", "run", "-m", "src.process_manager"]
