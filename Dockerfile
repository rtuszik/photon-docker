FROM adoptopenjdk/openjdk11:jdk-11.0.11_9

# Set the working directory
WORKDIR /app

# Install necessary tools
RUN apt-get update && apt-get install -y wget pbzip2 curl

# Define build argument for Photon version
ARG PHOTON_VERSION

# Download the specified Photon release
RUN wget https://github.com/komoot/photon/releases/download/${PHOTON_VERSION}/photon-${PHOTON_VERSION}.jar -O photon.jar

# Copy the startup script
COPY start-photon.sh /app/start-photon.sh
RUN chmod +x /app/start-photon.sh

# Expose the default Photon port
EXPOSE 2322

# Set the command to run the startup script
CMD ["/app/start-photon.sh"]
