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
    # Production WSGI server. Transcript OCR can take tens of seconds, hence the long timeout.
    # Each worker loads the OCR model, so raise WEB_CONCURRENCY only with memory to spare.
    exec uv run gunicorn \
        --bind "0.0.0.0:${PORT:-5000}" \
        --workers "${WEB_CONCURRENCY:-2}" \
        --timeout "${GUNICORN_TIMEOUT:-120}" \
        --graceful-timeout 30 \
        --access-logfile - \
        "app:create_app()"
fi
