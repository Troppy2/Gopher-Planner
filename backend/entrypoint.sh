#!/bin/sh
set -e

echo "Applying database migrations..."
uv run flask --app app db upgrade

echo "Starting Flask API..."

if [ "${FLASK_ENVIRONMENT:-development}" = "development" ]; then
    exec uv run flask --app app run \
        --host=0.0.0.0 \
        --port="${PORT:-5000}" \
        --debug
else
    exec uv run flask --app app run \
        --host=0.0.0.0 \
        --port="${PORT:-5000}"
fi