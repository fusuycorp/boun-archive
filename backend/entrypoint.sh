#!/bin/sh

# Stop on any error
set -e

echo "Starting backend environment initialization..."

# 1. Wait for services (PG & Meilisearch) to accept connections
python wait_for_services.py

# 2. Check distributed lock for initialization
if python wait_for_services.py --check-lock; then
    # We acquired the lock, run migrations and sync
    echo "Executing PostgreSQL database migrations..."
    PYTHONPATH=. python scripts/migrate_to_pg.py

    echo "Synchronizing search index in Meilisearch..."
    PYTHONPATH=. python scripts/sync_meilisearch.py
    
    # Mark as done
    python wait_for_services.py --mark-done
else
    echo "Skipping migration and sync as another instance is handling it."
fi

# 4. Start FastAPI server
echo "Starting FastAPI application via Uvicorn on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WEB_CONCURRENCY:-1}"
