#!/bin/sh

chown -R photon:photon /photon

exec gosu photon "$@"
