#!/bin/sh

# Stop on any error
set -e

echo "Starting backend environment initialization..."

# 1. Wait for services (PG & Meilisearch) to accept connections
python wait_for_services.py

# 2. Run Database Migration (checks for existing data to preserve persistence)
echo "Executing PostgreSQL database migrations..."
PYTHONPATH=. python scripts/migrate_to_pg.py

# 3. Sync Meilisearch
echo "Synchronizing search index in Meilisearch..."
PYTHONPATH=. python scripts/sync_meilisearch.py

# 4. Start FastAPI server
echo "Starting FastAPI application via Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
