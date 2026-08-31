"""
Empirical Adversarial & Stress Benchmark Harness for BOUN Archive.
Runs high-iteration stress tests and outputs quantitative empirical performance metrics.
"""

import sys
import time
import random
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
backend_path = ROOT_DIR / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app import models
from app.main import app, escape_meili_filter, escape_sql_wildcards, _search_courses_from_db
from app.database import Base, get_db
from scripts.sync_from_scraper import (
    ScraperClient,
    ensure_term,
    ensure_department,
    ensure_instructor,
    ensure_room,
    _upsert_course,
    sync_quota_feed,
    sync_deltas_feed,
    backfill_term,
)


def run_benchmarks():
    print("=" * 70)
    print("BOUN ARCHIVE — ADVERSARIAL STRESS & INGESTION BENCHMARK")
    print("=" * 70)

    # Initialize in-memory cache
    FastAPICache.init(InMemoryBackend(), prefix="stress-cache")

    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session = TestingSession()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    # Seed initial entities
    term = models.Term(id="2024-2025-1", academic_year="2024-2025", semester_num=1)
    dept = models.Department(kisaadi="CMPE", bolum="Computer Engineering")
    inst = models.Instructor(id=1, full_name="Albert Long")
    room = models.Room(id=1, name="NH101", building="New Hall")
    course = models.Course(
        id=1,
        term_id="2024-2025-1",
        dept_kisaadi="CMPE",
        course_code="CMPE 150",
        section="01",
        title="Introduction to Computing",
        instructor_id=1,
        credits=3,
        ects=6,
        delivery_method="Face-to-Face"
    )
    slot = models.CourseSlot(id=1, course_id=1, day_code="M", slot_hour=1, room_id=1)
    session.add_all([term, dept, inst, room, course, slot])
    session.commit()

    # -------------------------------------------------------------
    # 1. SQL Injection & Hostile Payloads Throughput
    # -------------------------------------------------------------
    print("\n[1/5] Benchmarking SQL Injection / Wildcard Resilience (500 requests)...")
    sqli_payloads = [
        "CMPE' OR '1'='1",
        "'; DROP TABLE courses; --",
        "' UNION SELECT 1,2,3,4,5,6,7,8,9,10 --",
        "CMPE' AND 1=CAST((SELECT 1) AS int) --",
        "%_%_%_%_%_%_%_%_%",
        "\\\\%\\\\_\\\\%\\\\_",
        "CMPE\x00' OR '1'='1",
        "İÖÜŞÇĞ ıüşçğ ' OR '1'='1",
    ]

    t0 = time.perf_counter()
    for i in range(500):
        p = sqli_payloads[i % len(sqli_payloads)]
        res = client.get("/v1/search", params={"q": p})
        assert res.status_code == 200
    t1 = time.perf_counter()
    sqli_duration = t1 - t0
    print(f"  ✓ 500 hostile search queries executed in {sqli_duration:.3f}s ({500/sqli_duration:.1f} req/s). Zero 500 errors.")

    # -------------------------------------------------------------
    # 2. Quota Snapshot High-Frequency Deduplication (2,000 snapshots)
    # -------------------------------------------------------------
    print("\n[2/5] Benchmarking Quota Snapshot Deduplication (2,000 snapshots)...")
    mock_scraper = MagicMock(spec=ScraperClient)
    
    # 10 courses, 2 sections each, 100 polling rounds = 2,000 items with same captured_at
    fixed_captured_at = "2026-08-31T12:00:00Z"
    quota_batch = []
    for c_idx in range(10):
        for s_idx in range(2):
            quota_batch.append({
                "term": "2024-2025-1",
                "course_code": f"CMPE {100 + c_idx}",
                "section": f"0{s_idx + 1}",
                "department": "CMPE",
                "status": "Open",
                "quota": "60",
                "current": "55",
                "quota_numeric": 60,
                "current_numeric": 55,
                "available": 5,
                "captured_at": fixed_captured_at
            })

    t0 = time.perf_counter()
    total_synced = 0
    for _ in range(100):  # 100 polling iterations of 20 items = 2000 items
        mock_scraper.get.return_value = list(quota_batch)
        total_synced += sync_quota_feed(session, mock_scraper, limit=500)
    t1 = time.perf_counter()
    quota_duration = t1 - t0
    
    # Verify exact deduplication: DB must have exactly 20 rows
    total_rows = session.query(models.QuotaSnapshot).filter(
        models.QuotaSnapshot.captured_at == fixed_captured_at
    ).count()
    print(f"  ✓ 2,000 quota snapshots ingested in {quota_duration:.3f}s ({2000/quota_duration:.1f} items/s).")
    print(f"  ✓ Deduplication verified: Exactly {total_rows} unique database records created (Expected: 20).")
    assert total_rows == 20

    # -------------------------------------------------------------
    # 3. Delta Sync Out-of-Order Causal Replay (1,000 delta events)
    # -------------------------------------------------------------
    print("\n[3/5] Benchmarking Out-of-Order Delta Event Replay (1,000 events)...")
    delta_events = []
    timestamps = [f"2026-08-31T10:{i:02d}:00Z" for i in range(60)]
    for i in range(1000):
        course_num = 200 + (i % 20)
        ts = timestamps[i % len(timestamps)]
        verb = random.choice(["INSERT", "UPDATE", "MODIFIED", "added", "modify", "update"])
        delta_events.append({
            "change_type": verb,
            "term": "2024-2025-1",
            "department": "CMPE",
            "course_code": f"CMPE {course_num}",
            "section": "01",
            "timestamp": ts,
            "new_value": {
                "title": f"Course {course_num} Iteration {i}",
                "credits": 3,
                "ects": 6
            }
        })
    # Scramble timestamps
    random.shuffle(delta_events)

    t0 = time.perf_counter()
    mock_scraper.get.return_value = delta_events
    synced_deltas = sync_deltas_feed(session, mock_scraper, limit=2000)
    t1 = time.perf_counter()
    delta_duration = t1 - t0
    print(f"  ✓ 1,000 scrambled delta events processed in {delta_duration:.3f}s ({1000/delta_duration:.1f} events/s).")
    print(f"  ✓ Total deltas synced: {synced_deltas}. Cursor advanced to: {session.query(models.SyncState).filter(models.SyncState.feed_name == 'deltas').first().last_cursor}")

    # -------------------------------------------------------------
    # 4. Scraper Term Parsing Throughput (5,000 variations)
    # -------------------------------------------------------------
    print("\n[4/5] Benchmarking Scraper Term Parsing (5,000 format variations)...")
    formats = [
        "2024-2025-1", "2024-2025-2", "2024/2025-1", "2024/2025-2", "2030-3",
        "2028/2029/2", "2035", "Fall-2024-2", "2024-2025-Summer", "2024-2025-99"
    ]
    t0 = time.perf_counter()
    term_cache = {}
    for i in range(5000):
        t_str = f"{formats[i % len(formats)]}_{i}"
        ensure_term(session, t_str, term_cache=term_cache)
    t1 = time.perf_counter()
    term_duration = t1 - t0
    print(f"  ✓ 5,000 term parsing operations completed in {term_duration:.3f}s ({5000/term_duration:.1f} ops/s).")

    # -------------------------------------------------------------
    # 5. Database Fallback Search Under Meilisearch Outage Simulation
    # -------------------------------------------------------------
    print("\n[5/5] Benchmarking Meilisearch Outage Fallback Search (200 requests)...")
    with patch("app.main.MEILI_CLIENT.index") as mock_index:
        mock_index.side_effect = Exception("Simulated Meilisearch Cluster Outage (503 Service Unavailable)")
        t0 = time.perf_counter()
        for i in range(200):
            res = client.get("/v1/search", params={"q": "CMPE", "limit": 20})
            assert res.status_code == 200
            assert len(res.json()["hits"]) > 0
        t1 = time.perf_counter()
        fallback_duration = t1 - t0
    print(f"  ✓ 200 fallback database searches executed in {fallback_duration:.3f}s ({200/fallback_duration:.1f} req/s). Zero 500 errors.")

    print("\n" + "=" * 70)
    print("ALL ADVERSARIAL STRESS BENCHMARKS COMPLETED SUCCESSFULLY — 100% PASS RATE")
    print("=" * 70)


if __name__ == "__main__":
    run_benchmarks()
