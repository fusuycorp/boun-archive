import os
import time
import psycopg2
import meilisearch
import redis
from dotenv import load_dotenv

load_dotenv()

def wait_for_postgres():
    db_url = os.getenv("DATABASE_URL", "postgresql://boun_user:boun_password@localhost/boun_archive")
    print(f"Waiting for PostgreSQL to be ready on: {db_url}...")
    start_time = time.time()
    while True:
        try:
            conn = psycopg2.connect(db_url)
            conn.close()
            print("PostgreSQL is ready!")
            break
        except Exception as e:
            if time.time() - start_time > 120:
                print("Timeout waiting for PostgreSQL.")
                raise e
            time.sleep(2)

def wait_for_meilisearch():
    meili_url = os.getenv("MEILI_URL", "http://localhost:7700")
    meili_key = os.getenv("MEILI_MASTER_KEY", "masterKey123")
    print(f"Waiting for Meilisearch to be ready on: {meili_url}...")
    client = meilisearch.Client(meili_url, meili_key)
    start_time = time.time()
    while True:
        try:
            health = client.health()
            if health.get("status") == "available":
                print("Meilisearch is ready!")
                break
        except Exception as e:
            if time.time() - start_time > 120:
                print("Timeout waiting for Meilisearch.")
                raise e
            time.sleep(2)

def wait_for_redis():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    print(f"Waiting for Redis to be ready on: {redis_url}...")
    client = redis.from_url(redis_url)
    start_time = time.time()
    while True:
        try:
            client.ping()
            print("Redis is ready!")
            return client # Return the client for reuse
        except Exception as e:
            if time.time() - start_time > 120:
                print("Timeout waiting for Redis.")
                raise e
            time.sleep(2)

def acquire_init_lock(redis_client):
    """
    Attempts to acquire a lock to perform initialization.
    Returns True if this instance should run init, False otherwise.
    """
    lock_key = "boun_archive_init_lock"
    done_key = "boun_archive_init_done"
    
    # If already done, don't run
    if redis_client.get(done_key):
        print("Initialization already completed by another instance.")
        return False
        
    # Try to acquire lock (expires in 10 minutes)
    if redis_client.set(lock_key, "locked", nx=True, ex=600):
        print("Acquired initialization lock.")
        return True
    
    # If couldn't acquire, wait for done_key
    print("Another instance is performing initialization. Waiting...")
    start_time = time.time()
    while not redis_client.get(done_key):
        if time.time() - start_time > 300: # 5 minute timeout
            print("Timeout waiting for another instance to finish initialization.")
            # Break and try to start anyway
            break
        time.sleep(5)
    
    print("Initialization confirmed complete by another instance.")
    return False

def mark_init_done(redis_client):
    """Mark initialization as complete and release the lock."""
    redis_client.set("boun_archive_init_done", "true", ex=86400) # Keep 'done' for 24h
    redis_client.delete("boun_archive_init_lock")
    print("Initialization marked as done.")

if __name__ == "__main__":
    wait_for_postgres()
    wait_for_meilisearch()
    r_client = wait_for_redis()
    
    # If run as a script, we can check if we should proceed with migrations
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--check-lock":
        if acquire_init_lock(r_client):
            sys.exit(0) # Proceed
        else:
            sys.exit(1) # Skip
    elif len(sys.argv) > 1 and sys.argv[1] == "--mark-done":
        mark_init_done(r_client)
        sys.exit(0)

