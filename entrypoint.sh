#!/bin/sh

PUID=${PUID:-9011}
PGID=${PGID:-9011}

CURRENT_UID=$(id -u photon 2>/dev/null || echo "0")
CURRENT_GID=$(id -g photon 2>/dev/null || echo "0")

if [ "$CURRENT_GID" != "$PGID" ]; then
    echo "Updating photon group GID from $CURRENT_GID to $PGID"
    groupmod -o -g "$PGID" photon
fi

if [ "$CURRENT_UID" != "$PUID" ]; then
    echo "Updating photon user UID from $CURRENT_UID to $PUID"
    usermod -o -u "$PUID" photon
fi

if [ -d "/photon/data/photon_data/node_1" ]; then
    if [ -d "/photon/data/node_1" ]; then
        echo "Removing old index..."
        rm -rf /photon/data/node_1
        echo "Cleanup complete: removed /photon/data/node_1"
    fi
elif [ -d "/photon/data/node_1" ]; then
    echo "Migrating data structure..."
    mkdir -p /photon/data/photon_data
    mv /photon/data/node_1 /photon/data/photon_data/
    echo "Migration complete: moved node_1 to /photon/data/photon_data/"
fi

chown -R photon:photon /photon
exec gosu photon "$@"
