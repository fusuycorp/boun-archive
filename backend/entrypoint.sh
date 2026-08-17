#!/bin/sh

# Stop on any error
set -e

echo "Starting backend environment..."

# 0. Allow overriding the default (e.g. the `init` job runs `python scripts/init_all.py`)
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

# 1. Wait for services (PostgreSQL, Meilisearch, Redis) to accept connections
python wait_for_services.py

# 2. Start FastAPI application server immediately
echo "Starting FastAPI application via Uvicorn on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WEB_CONCURRENCY:-1}"
