#!/bin/sh
set -e

echo "Running initial Python setup..."
uv run main.py

echo "Setup complete. Handing over to supervisord."
exec "$@"
