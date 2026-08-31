import sys
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import models
from scripts.sync_from_scraper import (
    ScraperClient,
    ensure_term,
    ensure_department,
    ensure_instructor,
    ensure_room,
    _upsert_course,
    _apply_delta_event,
    sync_quota_feed,
    sync_deltas_feed,
    backfill_term,
    sync_upstream_run_metadata,
    sync_meili_documents,
)


# ==============================================================================
# TIER 3 - Cross-Feature Combinations (10 comprehensive tests)
# ==============================================================================

def test_cross_01_ingestion_to_db_and_meili_search_resolution(client: TestClient, db_session: Session, monkeypatch):
    """1. Ingestion -> Database Model -> Meilisearch Sync -> Search API resolution."""
    # Step 1: Scraper backfill ingests courses
    client_mock = MagicMock(spec=ScraperClient)
    client_mock.get.return_value = [
        {
            "course_code": "CHEM 105",
            "section": "01",
            "department": "CHEM",
            "course_name": "General Chemistry I",
            "instructor": "Marie Curie",
            "credits": 4,
            "ects": 6,
            "slots": [{"day": "M", "hour": 2, "room": "KB301"}]
        },
        {
            "course_code": "CHEM 106",
            "section": "01",
            "department": "CHEM",
            "course_name": "General Chemistry II",
            "instructor": "Marie Curie",
            "credits": 4,
            "ects": 6,
            "slots": [{"day": "W", "hour": 4, "room": "KB301"}]
        }
    ]

    mock_meili_index = MagicMock()
    count = backfill_term(db_session, client_mock, meili_index=mock_meili_index, term_id="2024-2025-1")
    assert count == 2

    # Step 2: Verify meilisearch document sync format
    mock_meili_index.add_documents.assert_called()
    synced_docs = mock_meili_index.add_documents.call_args[0][0]
    assert any(d["course_code"] == "CHEM 105" for d in synced_docs)
    assert any(d["instructor"] == "Marie Curie" for d in synced_docs)

    # Step 3: Search API query resolution via DB fallback / Meili
    res = client.get("/v1/search?q=Marie%20Curie")
    assert res.status_code == 200
    data = res.json()
    assert len(data["hits"]) >= 2
    assert any("CHEM 105" in h["course_code"] for h in data["hits"])


def test_cross_02_delta_update_to_changelog_and_course_detail(client: TestClient, db_session: Session):
    """2. Scraper Delta Event (UPDATE) -> Course Change Log -> Database Reflection -> Detail API."""
    # Initial course exists (CMPE 150)
    c = db_session.query(models.Course).filter(models.Course.course_code == "CMPE 150").first()
    assert c is not None
    course_id = c.id

    client_mock = MagicMock(spec=ScraperClient)
    client_mock.get.return_value = [
        {
            "change_type": "modified",
            "term": "2024-2025-1",
            "department": "CMPE",
            "course_code": "CMPE 150",
            "section": "01",
            "timestamp": "2026-08-31T08:00:00Z",
            "old_value": {"title": "Old Title", "credits": 3},
            "new_value": {"title": "Computing Paradigms", "credits": 4, "ects": 7},
            "details": "Syllabus revision"
        }
    ]

    sync_deltas_feed(db_session, client_mock, limit=100)

    # Verify detail API reflects the change
    res_detail = client.get(f"/v1/courses/{course_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["title"] == "Computing Paradigms"
    assert res_detail.json()["credits"] == 4

    # Verify change log API reflects the audit record
    res_changes = client.get("/v1/courses/CMPE 150/changes")
    assert res_changes.status_code == 200
    changes = res_changes.json()
    assert any(ch["details"] == "Syllabus revision" for ch in changes)


def test_cross_03_delta_delete_to_meili_pruning_and_search(client: TestClient, db_session: Session):
    """3. Scraper Delta Event (DELETE) -> Meilisearch Prune -> Course History / Search."""
    # Seed course to delete
    c_temp = models.Course(
        id=703,
        term_id="2024-2025-1",
        dept_kisaadi="CMPE",
        course_code="CMPE 703",
        section="01",
        title="Temporary Seminar"
    )
    db_session.merge(c_temp)
    db_session.commit()

    mock_meili = MagicMock()
    client_mock = MagicMock(spec=ScraperClient)
    client_mock.get.return_value = [
        {
            "change_type": "removed",
            "term": "2024-2025-1",
            "department": "CMPE",
            "course_code": "CMPE 703",
            "section": "01",
            "timestamp": "2026-08-31T09:00:00Z",
            "details": "Course cancelled"
        }
    ]

    sync_deltas_feed(db_session, client_mock, meili_index=mock_meili, limit=100)

    # Verify Meilisearch pruning called
    mock_meili.delete_document.assert_called_with(703)

    # Verify detail endpoint returns 404
    res_detail = client.get("/v1/courses/703")
    assert res_detail.status_code == 404

    # Verify search returns 0 hits for deleted course
    res_search = client.get("/v1/search?q=CMPE%20703")
    assert res_search.status_code == 200
    assert not any(h["course_code"] == "CMPE 703" for h in res_search.json()["hits"])


def test_cross_04_quota_snapshots_to_deduplicated_history(client: TestClient, db_session: Session):
    """4. Quota Snapshot Ingestion -> Deduplication -> Quota History Timeline API."""
    client_mock = MagicMock(spec=ScraperClient)
    # Simulate multiple capture waves
    client_mock.get.return_value = [
        {
            "term": "2024-2025-1",
            "course_code": "CMPE 250",
            "section": "01",
            "department": "CMPE",
            "status": "Open",
            "quota": "60",
            "current": "20",
            "quota_numeric": 60,
            "current_numeric": 20,
            "available": 40,
            "captured_at": "2026-08-31T09:00:00Z"
        },
        {
            "term": "2024-2025-1",
            "course_code": "CMPE 250",
            "section": "01",
            "department": "CMPE",
            "status": "Open",
            "quota": "60",
            "current": "50",
            "quota_numeric": 60,
            "current_numeric": 50,
            "available": 10,
            "captured_at": "2026-08-31T10:00:00Z"
        }
    ]

    synced = sync_quota_feed(db_session, client_mock, limit=100)
    assert synced == 2

    # Query latest snapshot
    res_latest = client.get("/v1/courses/CMPE 250/quota")
    assert res_latest.status_code == 200
    data_latest = res_latest.json()
    assert len(data_latest) >= 1
    assert data_latest[0]["course_code"] == "CMPE 250"

    # Query full history timeline
    res_hist = client.get("/v1/courses/CMPE 250/quota?history=true")
    assert res_hist.status_code == 200
    data_hist = res_hist.json()
    assert len(data_hist) >= 2
    # Ensure ordered newest first
    assert data_hist[0]["captured_at"] >= data_hist[1]["captured_at"]


def test_cross_05_backfill_to_department_analytics(client: TestClient, db_session: Session):
    """5. Backfill Term Ingestion -> Department Discovery -> Department Unique Courses & Instructors API."""
    client_mock = MagicMock(spec=ScraperClient)
    client_mock.get.return_value = [
        {
            "course_code": "ECON 101",
            "section": "01",
            "department": "ECON",
            "course_name": "Microeconomics",
            "instructor": "Adam Smith",
            "credits": 3,
            "ects": 5,
            "slots": []
        },
        {
            "course_code": "ECON 102",
            "section": "01",
            "department": "ECON",
            "course_name": "Macroeconomics",
            "instructor": "Adam Smith",
            "credits": 3,
            "ects": 5,
            "slots": []
        }
    ]

    backfill_term(db_session, client_mock, term_id="2024-2025-1")

    # Verify unique courses endpoint
    res_courses = client.get("/v1/departments/ECON/unique-courses")
    assert res_courses.status_code == 200
    codes = [c["course_code"] for c in res_courses.json()]
    assert "ECON 101" in codes
    assert "ECON 102" in codes

    # Verify department instructors endpoint
    res_inst = client.get("/v1/departments/ECON/instructors")
    assert res_inst.status_code == 200
    smith = next((i for i in res_inst.json() if i["full_name"] == "Adam Smith"), None)
    assert smith is not None
    assert smith["course_count"] >= 2


def test_cross_06_backfill_to_instructor_dna_legacy(client: TestClient, db_session: Session):
    """6. Backfill Term Ingestion -> Instructor Discovery -> Instructor Legacy DNA API."""
    # Seed Alan Turing teaching across multiple terms and slots
    t1 = ensure_term(db_session, "2022-2023-1")
    t2 = ensure_term(db_session, "2023-2024-1")
    inst_id = ensure_instructor(db_session, "Alan Turing", {})
    r_id = ensure_room(db_session, "TuringHall", {})

    c1 = models.Course(
        id=7061,
        term_id="2022-2023-1",
        dept_kisaadi="CMPE",
        course_code="CMPE 300",
        section="01",
        title="Theory of Computation",
        instructor_id=inst_id
    )
    s1 = models.CourseSlot(id=7061, course_id=7061, day_code="M", slot_hour=3, room_id=r_id)

    c2 = models.Course(
        id=7062,
        term_id="2023-2024-1",
        dept_kisaadi="CMPE",
        course_code="CMPE 300",
        section="01",
        title="Theory of Computation",
        instructor_id=inst_id
    )
    s2 = models.CourseSlot(id=7062, course_id=7062, day_code="M", slot_hour=3, room_id=r_id)

    db_session.merge(c1)
    db_session.merge(s1)
    db_session.merge(c2)
    db_session.merge(s2)
    db_session.commit()

    res = client.get(f"/v1/analytics/instructor/{inst_id}/legacy")
    assert res.status_code == 200
    data = res.json()
    assert data["instructor_name"] == "Alan Turing"
    assert data["total_semesters_taught"] == 2
    assert data["total_courses_taught"] == 2
    assert data["most_frequent_courses"]["CMPE 300"] == 2
    assert data["preferred_slots"][0]["day"] == "M"
    assert data["preferred_slots"][0]["hour"] == 3


def test_cross_07_multi_term_backfill_to_ghost_schedule(client: TestClient, db_session: Session):
    """7. Multi-term Backfill -> Ghost Schedule Reconstruction across terms."""
    term_a = ensure_term(db_session, "2021-2022-1")
    term_b = ensure_term(db_session, "2021-2022-2")
    room_id = ensure_room(db_session, "Auditorium-A", {})

    cA = models.Course(
        id=7071,
        term_id="2021-2022-1",
        dept_kisaadi="CMPE",
        course_code="CMPE 101",
        section="01",
        title="Term A Class"
    )
    sA = models.CourseSlot(id=7071, course_id=7071, day_code="Th", slot_hour=5, room_id=room_id)

    cB = models.Course(
        id=7072,
        term_id="2021-2022-2",
        dept_kisaadi="CMPE",
        course_code="CMPE 102",
        section="01",
        title="Term B Class"
    )
    sB = models.CourseSlot(id=7072, course_id=7072, day_code="F", slot_hour=2, room_id=room_id)

    db_session.merge(cA)
    db_session.merge(sA)
    db_session.merge(cB)
    db_session.merge(sB)
    db_session.commit()

    res_a = client.get("/v1/analytics/ghost-schedule/2021-2022-1")
    assert res_a.status_code == 200
    assert any(s["course_code"] == "CMPE 101" for s in res_a.json())
    assert not any(s["course_code"] == "CMPE 102" for s in res_a.json())

    res_b = client.get("/v1/analytics/ghost-schedule/2021-2022-2")
    assert res_b.status_code == 200
    assert any(s["course_code"] == "CMPE 102" for s in res_b.json())
    assert not any(s["course_code"] == "CMPE 101" for s in res_b.json())


def test_cross_08_multi_term_to_scheduling_heatmap(client: TestClient, db_session: Session):
    """8. Multi-term Backfill -> Macro Scheduling Heatmap across decades."""
    # Seed courses in 2010s vs 2020s
    t_2015 = ensure_term(db_session, "2015-2016-1")
    t_2025 = ensure_term(db_session, "2025-2026-1")
    r_id = ensure_room(db_session, "KB200", {})

    c1 = models.Course(id=7081, term_id="2015-2016-1", course_code="HIST 101", title="History")
    s1 = models.CourseSlot(id=7081, course_id=7081, day_code="W", slot_hour=8, room_id=r_id)

    c2 = models.Course(id=7082, term_id="2025-2026-1", course_code="HIST 201", title="Modern History")
    s2 = models.CourseSlot(id=7082, course_id=7082, day_code="W", slot_hour=8, room_id=r_id)

    db_session.merge(c1)
    db_session.merge(s1)
    db_session.merge(c2)
    db_session.merge(s2)
    db_session.commit()

    res_2010 = client.get("/v1/analytics/macro/scheduling-heatmap?decade=2010")
    assert res_2010.status_code == 200
    assert len(res_2010.json()) >= 1

    res_2020 = client.get("/v1/analytics/macro/scheduling-heatmap?decade=2020")
    assert res_2020.status_code == 200
    assert len(res_2020.json()) >= 1


def test_cross_09_scraper_sync_to_system_status_and_health(client: TestClient, db_session: Session):
    """9. Scraper Delta Ingestion -> System Status Cursor Update -> Healthcheck/Staleness."""
    now_str = "2026-08-31T11:00:00Z"
    client_mock = MagicMock(spec=ScraperClient)
    client_mock.get.return_value = [
        {"status": "completed", "completed_at": now_str}
    ]

    sync_upstream_run_metadata(db_session, client_mock, dry_run=False)

    res = client.get("/v1/system/status")
    assert res.status_code == 200
    data = res.json()
    assert data["last_scraped_at"] == now_str
    assert data["is_stale"] is False
    assert "upstream_run" in data["feeds"]


def test_cross_10_course_slot_conflict_and_ghost_reconstruction(client: TestClient, db_session: Session):
    """10. Course Slot Ingestion with Rooms -> Ghost Schedule conflict mapping."""
    room_id = ensure_room(db_session, "MainAuditorium", {})

    c1 = models.Course(
        id=7101,
        term_id="2024-2025-1",
        dept_kisaadi="CMPE",
        course_code="CMPE 501",
        section="01",
        title="Grad Seminar 1"
    )
    s1 = models.CourseSlot(id=7101, course_id=7101, day_code="M", slot_hour=4, room_id=room_id)

    c2 = models.Course(
        id=7102,
        term_id="2024-2025-1",
        dept_kisaadi="EE",
        course_code="EE 501",
        section="01",
        title="Grad Seminar 2"
    )
    s2 = models.CourseSlot(id=7102, course_id=7102, day_code="M", slot_hour=5, room_id=room_id)

    db_session.merge(c1)
    db_session.merge(s1)
    db_session.merge(c2)
    db_session.merge(s2)
    db_session.commit()

    res = client.get("/v1/analytics/ghost-schedule/2024-2025-1")
    assert res.status_code == 200
    slots = res.json()
    aud_slots = [s for s in slots if s["room_name"] == "MainAuditorium"]
    assert len(aud_slots) >= 2
    hours = [s["slot_hour"] for s in aud_slots]
    assert 4 in hours
    assert 5 in hours
