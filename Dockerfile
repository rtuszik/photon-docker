FROM ubuntu:noble AS builder

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get -y install --no-install-recommends \
    python3.12 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.10 /uv /usr/local/bin/

WORKDIR /build

COPY pyproject.toml uv.lock ./

ENV UV_PYTHON=/usr/bin/python3.12 \
    UV_PYTHON_PREFERENCE=only-system \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/photon/.venv

RUN uv sync --locked --no-dev --no-install-project


FROM eclipse-temurin:25.0.3_9-jre-noble@sha256:b27ca47660a8fa837e47a8533b9b1a3a430295cf29ca28d91af4fd121572dc29

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

ADD https://github.com/komoot/photon/releases/download/${PHOTON_VERSION}/photon-${PHOTON_VERSION}.jar /photon/photon.jar

COPY src/ ./src/
COPY entrypoint.sh .
COPY --from=builder /photon/.venv /photon/.venv

ENV PATH="/photon/.venv/bin:${PATH}" \
    VIRTUAL_ENV=/photon/.venv

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
CMD ["/photon/.venv/bin/python", "-m", "src.process_manager"]
