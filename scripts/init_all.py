import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pathutil import ROOT_DIR, add_import_paths

add_import_paths()

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from wait_for_services import wait_for_meilisearch, wait_for_postgres, wait_for_redis

from scripts.migrate_to_pg import migrate
from scripts.sync_from_scraper import invalidate_redis_cache
from scripts.sync_meilisearch import sync_meilisearch


def _find_alembic_ini() -> str:
    candidates = [
        os.path.join(os.getcwd(), "alembic.ini"),
        os.path.join(ROOT_DIR, "alembic.ini"),
        os.path.join(ROOT_DIR, "backend", "alembic.ini"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"alembic.ini not found in any of: {candidates}")


def run_alembic_migrations() -> None:
    """Apply Alembic schema revisions (including pg_trgm GIN & functional indexes)."""
    alembic_ini = _find_alembic_ini()
    cfg = Config(alembic_ini)
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        engine = create_engine(db_url)
        try:
            tables = set(inspect(engine).get_table_names())
        finally:
            engine.dispose()
        # Legacy DB initialized via Base.metadata.create_all without alembic_version:
        # stamp at 0001 so idempotent 0002..head migrations apply cleanly.
        if "courses" in tables and "alembic_version" not in tables:
            print("Existing schema detected without alembic_version; stamping revision 0001...")
            command.stamp(cfg, "0001")
    command.upgrade(cfg, "head")


def main():
    print("=== BOUN Archive Initialization Job Starting ===")
    
    # 1. Wait for dependent backend services
    wait_for_postgres()
    wait_for_meilisearch()
    wait_for_redis()
    
    # 2. Apply Alembic Schema Migrations (creates tables + GIN/functional indexes)
    print("Running Alembic schema migrations...")
    run_alembic_migrations()

    # 3. Seed Historical Data if PostgreSQL is empty
    print("Running historical data migration...")
    migrate()
    
    # 4. Synchronize Meilisearch Search Index
    print("Running Meilisearch sync...")
    sync_meilisearch()

    # 5. Clear stale cached API responses after schema/index init
    invalidate_redis_cache()
    
    print("=== BOUN Archive Initialization Job Finished Successfully ===")

if __name__ == "__main__":
    main()
