FROM adoptopenjdk/openjdk11:jdk-11.0.11_9

WORKDIR /app

RUN apt-get update && apt-get install -y wget pbzip2 curl

ARG PHOTON_VERSION

RUN wget https://github.com/komoot/photon/releases/download/${PHOTON_VERSION}/photon-${PHOTON_VERSION}.jar -O /app/photon.jar

COPY start-photon.sh /app/start-photon.sh
RUN chmod +x /app/start-photon.sh

RUN mkdir -p /app/photon_data

EXPOSE 2322

CMD ["/app/start-photon.sh"]
