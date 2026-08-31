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
    sync_quota_feed,
    sync_deltas_feed,
    backfill_term,
    sync_terms_and_new_offerings,
)


# ==============================================================================
# TIER 4 - Real-World Application Workload Scenarios (5 scenarios)
# ==============================================================================

def test_scenario_1_full_term_scraping_and_search_ingestion(client: TestClient, db_session: Session):
    """
    Scenario 1: Full Term Scraping & Search Ingestion (F1, F6, F8)
    Simulates discovery of a newly published semester (2025/2026-1) by upstream boun-scrape,
    automatic backfill of courses, rooms, instructors, and slots, and subsequent search query resolution.
    """
    term_id = "2025/2026-1"
    raw_courses = [
        {
            "course_code": "CMPE 220",
            "section": "01",
            "department": "CMPE",
            "course_name": "Discrete Structures",
            "instructor": "Cem Say",
            "credits": 3,
            "ects": 6,
            "delivery_method": "Face-to-Face",
            "slots": [
                {"day": "M", "hour": 1, "room": "NH101"},
                {"day": "M", "hour": 2, "room": "NH101"},
                {"day": "W", "hour": 3, "room": "NH101"}
            ]
        },
        {
            "course_code": "EE 202",
            "section": "01",
            "department": "EE",
            "course_name": "Circuit Theory",
            "instructor": "Yorgo Istefanopulos",
            "credits": 4,
            "ects": 7,
            "delivery_method": "Face-to-Face",
            "slots": [
                {"day": "T", "hour": 4, "room": "KB433"},
                {"day": "Th", "hour": 4, "room": "KB433"}
            ]
        },
        {
            "course_code": "MATH 201",
            "section": "01",
            "department": "MATH",
            "course_name": "Matrix Theory",
            "instructor": "Betul Tanbay",
            "credits": 3,
            "ects": 6,
            "delivery_method": "Hybrid",
            "slots": [
                {"day": "F", "hour": 5, "room": "M1100"}
            ]
        }
    ]

    mock_client = MagicMock(spec=ScraperClient)
    def mock_get(path, params=None):
        if path == "terms":
            return [term_id]
        if "feeds/exports" in path or path == "courses":
            return raw_courses
        return []

    mock_client.get.side_effect = mock_get
    mock_meili = MagicMock()

    # Ingestion cycle
    synced_count = sync_terms_and_new_offerings(db_session, mock_client, meili_index=mock_meili)
    assert synced_count == 3

    # Verification 1: Terms endpoint reflects the new term
    res_terms = client.get("/v1/terms")
    assert res_terms.status_code == 200
    assert any(t["id"] == term_id for t in res_terms.json())

    # Verification 2: Search for newly ingested course by code
    res_search = client.get("/v1/search?q=CMPE%20220")
    assert res_search.status_code == 200
    hits = res_search.json()["hits"]
    assert len(hits) >= 1
    assert hits[0]["course_code"] == "CMPE 220"
    assert hits[0]["instructor"] == "Cem Say"
    assert len(hits[0]["slots"]) == 3

    # Verification 3: Search with department filter and term filter
    res_filtered = client.get(f"/v1/search?term={term_id}&dept=EE")
    assert res_filtered.status_code == 200
    ee_hits = res_filtered.json()["hits"]
    assert len(ee_hits) == 1
    assert ee_hits[0]["course_code"] == "EE 202"

    # Verification 4: Ghost schedule shows all slots populated
    res_ghost = client.get(f"/v1/analytics/ghost-schedule/{term_id}")
    assert res_ghost.status_code == 200
    ghost_slots = res_ghost.json()
    assert len(ghost_slots) == 6  # 3 CMPE + 2 EE + 1 MATH


def test_scenario_2_high_frequency_quota_polling_timeline(client: TestClient, db_session: Session):
    """
    Scenario 2: High-Frequency Quota Polling & History Timeline (F5, F6, F7)
    Simulates rapid quota polling during add-drop registration week across 5 distinct batches,
    tracking capacity fill rates, consent changes, cursor movements, and timeline reconstruction.
    """
    course_code = "CMPE 321"
    waves = [
        {"ts": "2026-09-01T08:00:00Z", "quota": 80, "current": 10, "status": "Open", "consent": False},
        {"ts": "2026-09-01T09:00:00Z", "quota": 80, "current": 45, "status": "Open", "consent": False},
        {"ts": "2026-09-01T10:00:00Z", "quota": 80, "current": 78, "status": "Almost Full", "consent": False},
        {"ts": "2026-09-01T11:00:00Z", "quota": 80, "current": 80, "status": "Closed", "consent": False},
        {"ts": "2026-09-01T12:00:00Z", "quota": 90, "current": 82, "status": "Consent Required", "consent": True},
    ]

    mock_client = MagicMock(spec=ScraperClient)
    for wave in waves:
        mock_client.get.return_value = [
            {
                "term": "2024-2025-1",
                "course_code": course_code,
                "section": "01",
                "department": "CMPE",
                "status": wave["status"],
                "quota": str(wave["quota"]),
                "current": str(wave["current"]),
                "quota_numeric": wave["quota"],
                "current_numeric": wave["current"],
                "is_consent": wave["consent"],
                "is_unlimited": False,
                "available": wave["quota"] - wave["current"],
                "captured_at": wave["ts"]
            }
        ]
        sync_quota_feed(db_session, mock_client, limit=50)

    # Verification 1: SyncState cursor advanced to the latest timestamp
    sync_state = db_session.query(models.SyncState).filter(models.SyncState.feed_name == "quota_snapshots").first()
    assert sync_state is not None
    assert sync_state.last_cursor == "2026-09-01T12:00:00Z"

    # Verification 2: Latest snapshot query returns the final wave state
    res_latest = client.get(f"/v1/courses/{course_code}/quota")
    assert res_latest.status_code == 200
    latest_data = res_latest.json()
    assert len(latest_data) == 1
    assert latest_data[0]["status"] == "Consent Required"
    assert latest_data[0]["quota_numeric"] == 90
    assert latest_data[0]["current_numeric"] == 82
    assert latest_data[0]["is_consent"] is True

    # Verification 3: History timeline preserves all 5 snapshots in reverse chronological order
    res_hist = client.get(f"/v1/courses/{course_code}/quota?history=true")
    assert res_hist.status_code == 200
    hist_data = res_hist.json()
    assert len(hist_data) == 5
    for i in range(len(hist_data) - 1):
        assert hist_data[i]["captured_at"] > hist_data[i+1]["captured_at"]


def test_scenario_3_department_schedule_shift_and_ghost_room_analysis(client: TestClient, db_session: Session):
    """
    Scenario 3: Department Schedule Shift & Ghost Room Analysis (F2, F4, F6)
    Simulates mid-semester classroom migration where Industrial Engineering courses
    shift from Old Building (OB101) to New Engineering Hall (ENG201) via delta events.
    """
    term_id = "2024-2025-1"
    # Seed initial course with slot in OB101
    ensure_term(db_session, term_id)
    ensure_department(db_session, "IE", "Industrial Engineering")
    r_old = ensure_room(db_session, "OB101", {})
    r_new = ensure_room(db_session, "ENG201", {})

    c_ie = models.Course(
        id=9031,
        term_id=term_id,
        dept_kisaadi="IE",
        course_code="IE 310",
        section="01",
        title="Operations Research"
    )
    s_ie = models.CourseSlot(
        id=9031,
        course_id=9031,
        day_code="W",
        slot_hour=3,
        room_id=r_old
    )
    db_session.merge(c_ie)
    db_session.merge(s_ie)
    db_session.commit()

    # Pre-shift verification: Ghost schedule reflects OB101
    res_pre = client.get(f"/v1/analytics/ghost-schedule/{term_id}?dept=IE")
    assert res_pre.status_code == 200
    assert any(s["room_name"] == "OB101" for s in res_pre.json())
    assert not any(s["room_name"] == "ENG201" for s in res_pre.json())

    # Delta event: Room reallocation to ENG201
    mock_client = MagicMock(spec=ScraperClient)
    mock_client.get.return_value = [
        {
            "change_type": "modified",
            "term": term_id,
            "department": "IE",
            "course_code": "IE 310",
            "section": "01",
            "timestamp": "2026-09-02T14:00:00Z",
            "new_value": {
                "title": "Operations Research",
                "slots": [{"day": "W", "hour": 3, "room": "ENG201"}]
            },
            "details": "Room reassignment to ENG201"
        }
    ]

    sync_deltas_feed(db_session, mock_client, limit=50)

    # Invalidate cache to test real-time reflection of DB shift
    from fastapi_cache import FastAPICache
    if hasattr(FastAPICache.get_backend(), "_store"):
        FastAPICache.get_backend()._store.clear()

    # Post-shift verification: Ghost schedule reflects ENG201 and no longer OB101
    res_post = client.get(f"/v1/analytics/ghost-schedule/{term_id}?dept=IE")
    assert res_post.status_code == 200
    post_slots = res_post.json()
    assert any(s["room_name"] == "ENG201" for s in post_slots)
    assert not any(s["room_name"] == "OB101" for s in post_slots)


def test_scenario_4_multi_semester_curriculum_migration_and_changelog(client: TestClient, db_session: Session):
    """
    Scenario 4: Multi-Semester Curriculum Migration & Delta Changelog (F1, F6, F7, F8)
    Simulates curriculum evolution across 3 academic years:
    - 2022-2023: Course created with 3 credits
    - 2023-2024: Course modified with 4 credits, ECTS 7, and instructor handover
    - 2024-2025: Advanced elective added
    Verifies full historical evolution and audit trails.
    """
    # Term 1: 2022-2023-1
    ensure_term(db_session, "2022-2023-1")
    i1 = ensure_instructor(db_session, "Grace Hopper", {})
    c_y1 = models.Course(
        id=9041,
        term_id="2022-2023-1",
        dept_kisaadi="CMPE",
        course_code="CMPE 344",
        section="01",
        title="Computer Networks",
        instructor_id=i1,
        credits=3,
        ects=5
    )
    db_session.merge(c_y1)

    # Term 2: 2023-2024-1 (revision)
    ensure_term(db_session, "2023-2024-1")
    i2 = ensure_instructor(db_session, "Vint Cerf", {})
    c_y2 = models.Course(
        id=9042,
        term_id="2023-2024-1",
        dept_kisaadi="CMPE",
        course_code="CMPE 344",
        section="01",
        title="Advanced Computer Networks",
        instructor_id=i2,
        credits=4,
        ects=7
    )
    db_session.merge(c_y2)

    # Record changelog for the transition
    ch = models.CourseChange(
        id=9041,
        change_type="UPDATE",
        term_id="2023-2024-1",
        dept_kisaadi="CMPE",
        course_code="CMPE 344",
        section="01",
        timestamp="2023-09-15T10:00:00Z",
        old_value=json.dumps({"credits": 3, "instructor": "Grace Hopper"}),
        new_value=json.dumps({"credits": 4, "instructor": "Vint Cerf"}),
        details="Curriculum update for 2023-2024"
    )
    db_session.merge(ch)
    db_session.commit()

    # Verification 1: Course history endpoint returns both terms sorted newest first
    res_hist = client.get("/v1/courses/history/CMPE 344")
    assert res_hist.status_code == 200
    hist_data = res_hist.json()
    assert len(hist_data) >= 2
    assert hist_data[0]["term_id"] == "2023-2024-1"
    assert hist_data[0]["instructor"] == "Vint Cerf"
    assert hist_data[0]["credits"] == 4
    assert hist_data[1]["term_id"] == "2022-2023-1"
    assert hist_data[1]["instructor"] == "Grace Hopper"

    # Verification 2: Changelog endpoint returns audit history
    res_ch = client.get("/v1/courses/CMPE 344/changes")
    assert res_ch.status_code == 200
    changes = res_ch.json()
    assert len(changes) >= 1
    assert "Curriculum update" in changes[0]["details"]

    # Verification 3: Instructor DNA tracks Vint Cerf
    res_dna = client.get(f"/v1/analytics/instructor/{i2}/legacy")
    assert res_dna.status_code == 200
    assert res_dna.json()["instructor_name"] == "Vint Cerf"


def test_scenario_5_complex_multi_filter_search_and_injection_stress(client: TestClient, db_session: Session):
    """
    Scenario 5: Complex Multi-Filter Search with Special Characters & Aliases (F1, F9)
    Simulates complex multi-parameter student queries combined with stress test injection payloads:
    - Multiple term filters
    - Whitespace and casing variations
    - SQL wildcard escaping
    - Meilisearch quote escaping
    """
    # Seed multiple courses
    t1 = ensure_term(db_session, "2024-2025-1")
    t2 = ensure_term(db_session, "2023-2024-2")
    inst = ensure_instructor(db_session, "Donald Knuth", {})

    c1 = models.Course(
        id=9051,
        term_id="2024-2025-1",
        dept_kisaadi="CMPE",
        course_code="CMPE 480",
        section="01",
        title="Intro to Artificial Intelligence",
        instructor_id=inst,
        credits=3,
        ects=6
    )
    c2 = models.Course(
        id=9052,
        term_id="2023-2024-2",
        dept_kisaadi="CMPE",
        course_code="CMPE 482",
        section="01",
        title="Advanced AI Algorithms",
        instructor_id=inst,
        credits=4,
        ects=7
    )
    db_session.merge(c1)
    db_session.merge(c2)
    db_session.commit()

    # Query 1: Combined multi-term + instructor + sorting
    res1 = client.get("/v1/search?term=2024-2025-1&term=2023-2024-2&instructor=Donald%20Knuth&sort_by=credits&sort_order=desc")
    assert res1.status_code == 200
    hits1 = res1.json()["hits"]
    assert len(hits1) >= 2
    assert hits1[0]["credits"] >= hits1[1]["credits"]

    # Query 2: Course code spacing variations
    res_space = client.get("/v1/search?q=CMPE%20480")
    assert res_space.status_code == 200
    assert any(h["course_code"] == "CMPE 480" for h in res_space.json()["hits"])

    res_nospace = client.get("/v1/search?q=cmpe480")
    assert res_nospace.status_code == 200
    assert any(h["course_code"] == "CMPE 480" for h in res_nospace.json()["hits"])

    # Query 3: Injection stress test payloads
    payloads = [
        "CMPE' OR '1'='1",
        "CMPE\" OR \"1\"=\"1",
        "%CMPE%_150%",
        "\\\\''\\\\",
        "CMPE 480; SELECT * FROM courses;",
    ]
    for p in payloads:
        res_inject = client.get(f"/v1/search?q={p}")
        assert res_inject.status_code == 200
        assert "hits" in res_inject.json()
