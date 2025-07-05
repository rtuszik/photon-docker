FROM eclipse-temurin:21.0.5_11-jre-noble
# install astral uv
COPY --from=ghcr.io/astral-sh/uv:0.7.19 /uv /uvx /bin/

ARG DEBIAN_FRONTEND=noninteractive
ARG PHOTON_VERSION
ARG PUID=9011
ARG PGID=9011

RUN apt-get update \  
  && apt-get -y install --no-install-recommends \
  pbzip2 \
  wget \
  procps \
  coreutils \
  tree \
  gosu \
  && rm -rf /var/lib/apt/lists/*

RUN groupadd -g ${PGID} -o photon && \
    useradd -u ${PUID} -g photon -o -s /bin/false -m -d /photon photon

WORKDIR /photon


RUN mkdir -p /photon/photon_data

ADD https://github.com/komoot/photon/releases/download/${PHOTON_VERSION}/photon-opensearch-${PHOTON_VERSION}.jar /photon/photon.jar

COPY start-photon.sh ./start-photon.sh
COPY src/ ./src/
RUN chmod +x start-photon.sh src/*.sh && \
    chmod 644 /photon/photon.jar && \
    chown -R photon:photon /photon


VOLUME /photon/photon_data
EXPOSE 2322

ENTRYPOINT ["/photon/start-photon.sh"]
