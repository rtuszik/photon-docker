#!/bin/sh
set -e

echo "Running initial Python setup..."
uv run entrypoint.py

echo "Setup complete. Handing over to supervisord."
exec "$@"
