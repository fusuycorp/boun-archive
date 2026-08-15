import os
import sys

# Locate root directories (whether run from /app in container or repo root locally)
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
cwd = os.getcwd()

for p in [cwd, root_dir, os.path.join(root_dir, 'backend'), os.path.join(cwd, 'backend')]:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

try:
    from wait_for_services import wait_for_postgres, wait_for_meilisearch, wait_for_redis
except ImportError:
    from backend.wait_for_services import wait_for_postgres, wait_for_meilisearch, wait_for_redis

try:
    from scripts.migrate_to_pg import migrate
except ImportError:
    from migrate_to_pg import migrate

try:
    from scripts.sync_meilisearch import sync_meilisearch
except ImportError:
    from sync_meilisearch import sync_meilisearch

def main():
    print("=== BOUN Archive Initialization Job Starting ===")
    
    # 1. Wait for dependent backend services
    wait_for_postgres()
    wait_for_meilisearch()
    wait_for_redis()
    
    # 2. Run Database Migrations
    print("Running database migrations...")
    migrate()
    
    # 3. Synchronize Meilisearch Search Index
    print("Running Meilisearch sync...")
    sync_meilisearch()
    
    print("=== BOUN Archive Initialization Job Finished Successfully ===")

if __name__ == "__main__":
    main()
