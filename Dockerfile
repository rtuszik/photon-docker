FROM eclipse-temurin:21.0.5_11-jre-noble

# install astral uv
COPY --from=ghcr.io/astral-sh/uv:0.7.19 /uv /usr/local/bin/

ARG DEBIAN_FRONTEND=noninteractive
ARG PHOTON_VERSION
ARG PUID=9011
ARG PGID=9011

RUN apt-get update \
  && apt-get -y install --no-install-recommends \
  lbzip2 \
  gosu \
  python3.12 \
  && rm -rf /var/lib/apt/lists/*

RUN groupadd -g ${PGID} -o photon && \
    useradd -u ${PUID} -g photon -o -s /bin/false -m -d /photon photon

WORKDIR /photon

RUN mkdir -p /photon/data/

ADD https://github.com/komoot/photon/releases/download/${PHOTON_VERSION}/photon-opensearch-${PHOTON_VERSION}.jar /photon/photon.jar

COPY src/ ./src/
COPY entrypoint.py .
COPY entrypoint.sh .
COPY updater.py .
COPY process_manager.py .
COPY pyproject.toml .
COPY uv.lock .
RUN gosu photon uv sync --locked


RUN chmod 644 /photon/photon.jar && \
    chown -R photon:photon /photon

RUN gosu photon uv sync --locked

EXPOSE 2322

ENTRYPOINT ["/bin/sh", "entrypoint.sh"]
CMD ["uv", "run", "process_manager.py"]
