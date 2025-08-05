#!/bin/sh

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
