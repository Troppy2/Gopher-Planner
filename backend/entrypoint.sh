#!/bin/sh
set -e

echo "Applying database migrations..."
uv run flask --app app db upgrade

echo "Starting Flask API..."
exec uv run flask --app app run --host=0.0.0.0 --port=5000