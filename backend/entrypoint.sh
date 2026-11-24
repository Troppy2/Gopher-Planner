#!/bin/sh
set -e

# Local and Compose runs migrate on start. Production sets RUN_MIGRATIONS=false
# because CD applies migrations as a separate step before deploying.
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Applying database migrations..."
    uv run flask --app app db upgrade
fi

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
