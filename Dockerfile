FROM eclipse-temurin:21.0.5_11-jre-noble

ARG PHOTON_VERSION

RUN apt-get update \  
  && apt-get -y install --no-install-recommends \
  pbzip2 \
  wget \
  procps \
  coreutils \
  tree \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /photon

RUN mkdir -p /photon/photon_data

ADD https://github.com/komoot/photon/releases/download/${PHOTON_VERSION}/photon-${PHOTON_VERSION}.jar /photon/photon.jar

COPY start-photon.sh ./start-photon.sh
RUN chmod +x start-photon.sh


VOLUME /photon/photon_data
EXPOSE 2322

ENTRYPOINT ["/photon/start-photon.sh"]

