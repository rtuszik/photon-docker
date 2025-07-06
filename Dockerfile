FROM eclipse-temurin:21.0.5_11-jre-noble

# install astral uv
COPY --from=ghcr.io/astral-sh/uv:0.7.19 /uv /usr/local/bin/

ARG DEBIAN_FRONTEND=noninteractive
ARG PHOTON_VERSION
ARG PUID=9011
ARG PGID=9011

RUN apt-get update \
  && apt-get -y install --no-install-recommends \
  pbzip2 \
  gosu \
  python3.12 \
  cron \
  supervisor \
  && rm -rf /var/lib/apt/lists/*

RUN groupadd -g ${PGID} -o photon && \
    useradd -u ${PUID} -g photon -o -s /bin/false -m -d /photon photon

WORKDIR /photon

RUN mkdir -p /photon/photon_data

ADD https://github.com/komoot/photon/releases/download/${PHOTON_VERSION}/photon-opensearch-${PHOTON_VERSION}.jar /photon/photon.jar

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker-entrypoint.sh /usr/local/bin/
COPY src/ ./src/
COPY entrypoint.py .
COPY updater.py .
COPY pyproject.toml .
COPY uv.lock .
RUN uv sync --locked

RUN chmod +x /usr/local/bin/docker-entrypoint.sh && \
    chmod 644 /photon/photon.jar && \
    chown -R photon:photon /photon

RUN uv sync --locked

VOLUME /photon/photon_data
EXPOSE 2322

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
