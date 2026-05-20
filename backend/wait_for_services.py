import os
import time
import psycopg2
import meilisearch
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

if __name__ == "__main__":
    wait_for_postgres()
    wait_for_meilisearch()
