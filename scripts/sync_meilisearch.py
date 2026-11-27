import os
import sys
from contextlib import suppress

import meilisearch
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import joinedload, selectinload, sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pathutil import add_import_paths

add_import_paths()

from app.models import Course, CourseCatalog, CourseSlot
from app.sync import _build_meili_document, _extract_meili_task_uid, wait_meili_tasks

from scripts.sync_from_scraper import invalidate_redis_cache

load_dotenv()


def _extract_task_uid(task):
    return _extract_meili_task_uid(task)


def _wait_for_meili_task(client, task, timeout_in_ms: int = 30000):
    results = wait_meili_tasks(client, [task], timeout_in_ms=timeout_in_ms)
    return results[0] if results else None


def _prune_orphaned_docs(index, client, session) -> int:
    print("Checking for pruned/deleted courses in Meilisearch...")
    try:
        db_course_ids = {r[0] for r in session.query(Course.id).all()}
        offset = 0
        limit = 1000
        orphaned_ids = []
        while True:
            docs_res = index.get_documents({"fields": ["id"], "limit": limit, "offset": offset})
            if not docs_res or not docs_res.results:
                break
            for doc in docs_res.results:
                doc_id = getattr(doc, "id", None)
                if doc_id is not None and doc_id not in db_course_ids:
                    orphaned_ids.append(doc_id)
            if len(docs_res.results) < limit:
                break
            offset += limit

        if orphaned_ids:
            print(f"Pruning {len(orphaned_ids)} deleted course(s) from Meilisearch...")
            wait_meili_tasks(client, [index.delete_documents(orphaned_ids)], timeout_in_ms=30000)
            print(f"Pruned {len(orphaned_ids)} deleted course(s).")
            return len(orphaned_ids)
        print("No orphaned course documents to prune.")
        return 0
    except Exception as e:
        print(f"Warning: Document pruning check encountered an error: {e}")
        return 0


def _index_already_populated(index, session, force: bool) -> bool:
    if force or "--force" in sys.argv:
        return False
    with suppress(Exception):
        stats = index.get_stats()
        doc_count = getattr(stats, "number_of_documents", None)
        if doc_count is None and isinstance(stats, dict):
            doc_count = stats.get("numberOfDocuments", 0)
        db_count = session.query(Course.id).count()
        if doc_count and db_count and doc_count >= db_count:
            print(f"Meilisearch already contains {doc_count}/{db_count} indexed courses. Skipping sync (pass --force to re-sync).")
            return True
    return False


def _configure_meili_index(client, index) -> None:
    print("Ensuring index primaryKey='id' and configuring settings...")
    create_task = client.create_index("courses", {"primaryKey": "id"})
    try:
        _wait_for_meili_task(client, create_task, timeout_in_ms=30000)
    except RuntimeError as exc:
        if "index_already_exists" not in str(exc):
            raise
    update_pk_task = index.update(primary_key="id")
    try:
        _wait_for_meili_task(client, update_pk_task, timeout_in_ms=30000)
    except RuntimeError as exc:
        if "index_primary_key_already_exists" not in str(exc):
            raise
    config_task = index.update_settings(
        {
            "filterableAttributes": [
                "term",
                "dept_code",
                "department",
                "instructor",
                "instructor_id",
                "delivery_method",
                "has_syllabus",
            ],
            "searchableAttributes": [
                "course_code",
                "title",
                "instructor",
                "department",
                "catalog_text",
                "syllabus_snippet",
            ],
            "faceting": {"maxValuesPerFacet": 10000},
            "pagination": {"maxTotalHits": 200000},
            "sortableAttributes": ["term", "course_code", "title", "instructor", "credits", "ects"],
        }
    )
    _wait_for_meili_task(client, config_task, timeout_in_ms=30000)


def _push_course_chunks(client, index, session) -> int:
    print("Fetching catalog descriptions and courses from PostgreSQL...")
    catalog_map = {
        code: (text_val or "")[:4000]
        for code, text_val in session.query(CourseCatalog.course_code, CourseCatalog.canonical_text).all()
    }
    query = session.query(Course).options(
        joinedload(Course.term),
        joinedload(Course.department),
        joinedload(Course.instructor),
        selectinload(Course.slots).joinedload(CourseSlot.room),
    )

    print("Preparing and pushing documents to Meilisearch in chunks...")
    chunk_size = 2000
    chunk_count = 0
    documents = []
    queued_tasks = []

    for c in query.yield_per(chunk_size):
        documents.append(_build_meili_document(c, catalog_map))
        if len(documents) >= chunk_size:
            queued_tasks.append(index.add_documents(documents, primary_key="id"))
            chunk_count += 1
            if chunk_count % 10 == 0:
                print(f"Queued chunk {chunk_count}...")
            documents = []

    if documents:
        queued_tasks.append(index.add_documents(documents, primary_key="id"))
        chunk_count += 1
        print(f"Queued final chunk {chunk_count}")

    if queued_tasks:
        print(f"Awaiting indexing completion for {len(queued_tasks)} queued Meilisearch task(s)...")
        wait_meili_tasks(client, queued_tasks, timeout_in_ms=300000)

    return chunk_count


def sync_meilisearch(force: bool = False):
    print("Starting Meilisearch sync...")
    meili_url = os.getenv("MEILI_URL", "http://localhost:7700")
    meili_key = os.getenv("MEILI_MASTER_KEY")
    if not meili_key:
        raise RuntimeError("MEILI_MASTER_KEY is not set. Aborting sync.")

    client = meilisearch.Client(meili_url, meili_key, timeout=15)
    index = client.index("courses")

    engine = create_engine(os.getenv("DATABASE_URL"))
    session = sessionmaker(bind=engine)()
    chunks_pushed = 0
    pruned_count = 0
    try:
        if _index_already_populated(index, session, force):
            return
        _configure_meili_index(client, index)
        chunks_pushed = _push_course_chunks(client, index, session)
        pruned_count = _prune_orphaned_docs(index, client, session)
    finally:
        session.close()

    if chunks_pushed > 0 or pruned_count > 0:
        invalidate_redis_cache()

    print("Meilisearch sync completed!")

if __name__ == "__main__":
    force_sync = "--force" in sys.argv
    sync_meilisearch(force=force_sync)
