FROM adoptopenjdk/openjdk11
WORKDIR /app

# Define an argument to accept the Photon version
ARG PHOTON_VERSION

# Download the Photon JAR file for the specified version
RUN curl -L -o photon.jar https://github.com/komoot/photon/releases/download/${PHOTON_VERSION}/photon-${PHOTON_VERSION}.jar

EXPOSE 2322

# Run the Photon server
CMD ["java", "-jar", "photon.jar"]
