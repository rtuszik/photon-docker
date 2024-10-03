FROM eclipse-temurin:21.0.4_7-jre-noble

RUN apt-get update \  
  && apt-get -y install \
  pbzip2 \
  wget \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /photon
ARG PHOTON_VERSION

ADD https://github.com/komoot/photon/releases/download/${PHOTON_VERSION}/photon-${PHOTON_VERSION}.jar /photon/photon.jar

COPY start-photon.sh ./start-photon.sh
RUN chmod +x start-photon.sh


VOLUME /photon/photon_data
EXPOSE 2322

ENTRYPOINT ["/photon/start-photon.sh"]

