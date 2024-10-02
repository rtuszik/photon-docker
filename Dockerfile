FROM adoptopenjdk/openjdk11:jdk-11.0.11_9

WORKDIR /app

RUN apt-get update \
  && apt-get -y install \
  pbzip2 \
  wget \
  && rm -rf /var/lib/apt/lists/*

ARG PHOTON_VERSION

ADD https://github.com/komoot/photon/releases/download/${PHOTON_VERSION}/photon-${PHOTON_VERSION}.jar /app/photon.jar

COPY start-photon.sh /app/start-photon.sh

VOLUME /photon/photon_data


EXPOSE 2322

CMD ["/app/start-photon.sh"]

