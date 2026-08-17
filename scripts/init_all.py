import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pathutil import add_import_paths

add_import_paths()

from wait_for_services import wait_for_postgres, wait_for_meilisearch, wait_for_redis
from scripts.migrate_to_pg import migrate
from scripts.sync_meilisearch import sync_meilisearch

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
