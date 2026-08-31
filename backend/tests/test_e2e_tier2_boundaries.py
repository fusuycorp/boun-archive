import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import models
from app.main import escape_meili_filter, escape_sql_wildcards
from scripts.sync_from_scraper import (
    ScraperClient,
    clean_int,
    normalize_code,
    normalize_section,
    ensure_term,
    ensure_department,
    ensure_instructor,
    ensure_room,
    _upsert_course,
    _apply_delta_event,
    sync_quota_feed,
    sync_deltas_feed,
    backfill_term,
    sync_meili_documents,
)


# ==============================================================================
# TIER 2 - FEATURE 1: Course Search & Fallback (5 boundary tests)
# ==============================================================================

def test_t2_f1_01_search_empty_query_string(client: TestClient):
    """Empty query string returns default course list without errors."""
    res = client.get("/v1/search?q=")
    assert res.status_code == 200
    data = res.json()
    assert "hits" in data
    assert isinstance(data["hits"], list)

    res_ws = client.get("/v1/search?q=%20%20%20")
    assert res_ws.status_code == 200
    assert "hits" in res_ws.json()


def test_t2_f1_02_search_zero_results_query(client: TestClient):
    """Query with no matches returns empty hits list with totalHits = 0."""
    res = client.get("/v1/search?q=NONEXISTENT_XYZ_COURSE_9999")
    assert res.status_code == 200
    data = res.json()
    assert data["hits"] == []
    assert data.get("totalHits", 0) == 0


def test_t2_f1_03_search_sql_wildcards_and_injection(client: TestClient):
    """SQL wildcards and injection strings are safely escaped and handled."""
    # Test SQL injection string
    res_inject = client.get("/v1/search?q=CMPE'%20OR%20'1'='1")
    assert res_inject.status_code == 200
    assert isinstance(res_inject.json()["hits"], list)

    # Test DROP TABLE attempt
    res_drop = client.get("/v1/search?q=%25%3B%20DROP%20TABLE%20courses%3B%20--")
    assert res_drop.status_code == 200
    assert isinstance(res_drop.json()["hits"], list)


def test_t2_f1_04_search_invalid_sort_parameter(client: TestClient):
    """Invalid sort_by field returns 422 Unprocessable Entity."""
    res = client.get("/v1/search?sort_by=malicious_injected_column")
    assert res.status_code == 422
    assert "sort_by must be one of" in res.json()["detail"]


def test_t2_f1_05_search_limit_offset_boundaries(client: TestClient):
    """Limit and offset boundaries (0, 500, 10000) return 200; >500 returns 422."""
    # Valid limits
    res_zero = client.get("/v1/search?limit=0")
    assert res_zero.status_code == 200
    assert len(res_zero.json()["hits"]) == 0

    res_max = client.get("/v1/search?limit=500")
    assert res_max.status_code == 200

    res_offset = client.get("/v1/search?offset=10000")
    assert res_offset.status_code == 200

    # Exceeding bounds returns 422
    res_overflow = client.get("/v1/search?limit=501")
    assert res_overflow.status_code == 422

    res_neg = client.get("/v1/search?limit=-1")
    assert res_neg.status_code == 422


# ==============================================================================
# TIER 2 - FEATURE 2: Department Analytics & Evolution (5 boundary tests)
# ==============================================================================

def test_t2_f2_01_department_unique_courses_nonexistent_dept(client: TestClient):
    """Nonexistent department returns empty unique courses list without 500 crash."""
    res = client.get("/v1/departments/NONEXISTENT_DEPT/unique-courses")
    assert res.status_code == 200
    assert res.json() == []


def test_t2_f2_02_department_instructors_nonexistent_dept(client: TestClient):
    """Nonexistent department returns empty instructors list without 500 crash."""
    res = client.get("/v1/departments/NONEXISTENT_DEPT/instructors")
    assert res.status_code == 200
    assert res.json() == []


def test_t2_f2_03_department_unique_courses_null_titles(client: TestClient, db_session: Session):
    """Courses with null titles return empty string in unique courses without crashing."""
    c_null = models.Course(
        id=299,
        term_id="2024-2025-1",
        dept_kisaadi="CMPE",
        course_code="CMPE 199",
        section="01",
        title=None,
        instructor_id=1
    )
    db_session.merge(c_null)
    db_session.commit()

    res = client.get("/v1/departments/CMPE/unique-courses")
    assert res.status_code == 200
    cmpe199 = next((c for c in res.json() if c["course_code"] == "CMPE 199"), None)
    assert cmpe199 is not None
    assert cmpe199["title"] == ""


def test_t2_f2_04_department_special_character_dept_code(client: TestClient):
    """Department codes with whitespace/special characters handled safely."""
    res = client.get("/v1/departments/%20%20%20/unique-courses")
    assert res.status_code == 200
    assert res.json() == []


def test_t2_f2_05_department_evolution_empty_database():
    """MacroEngine department evolution handles empty database cleanly."""
    from app.analytics import MacroEngine
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    models.Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()

    res = MacroEngine.get_department_evolution(session)
    session.close()

    assert res["years"] == []
    assert res["departments"] == {}


# ==============================================================================
# TIER 2 - FEATURE 3: Instructor Analytics & Legacy (5 boundary tests)
# ==============================================================================

def test_t2_f3_01_instructor_detail_nonexistent_404(client: TestClient):
    """GET /v1/instructors/999999 returns 404 Not Found."""
    res = client.get("/v1/instructors/999999")
    assert res.status_code == 404
    assert res.json()["detail"] == "Instructor not found"


def test_t2_f3_02_instructor_legacy_nonexistent_404(client: TestClient):
    """GET /v1/analytics/instructor/999999/legacy returns 404 Not Found."""
    res = client.get("/v1/analytics/instructor/999999/legacy")
    assert res.status_code == 404
    assert res.json()["detail"] == "Instructor not found"


def test_t2_f3_03_instructor_legacy_zero_courses(client: TestClient, db_session: Session):
    """Instructor with 0 courses returns 0 counts and empty distributions."""
    inst_idle = models.Instructor(id=399, full_name="Idle Professor")
    db_session.merge(inst_idle)
    db_session.commit()

    res = client.get("/v1/analytics/instructor/399/legacy")
    assert res.status_code == 200
    data = res.json()
    assert data["total_semesters_taught"] == 0
    assert data["total_courses_taught"] == 0
    assert data["most_frequent_courses"] == {}
    assert data["preferred_slots"] == []
    assert data["history"] == []


def test_t2_f3_04_instructor_legacy_null_slots(client: TestClient, db_session: Session):
    """Course slots with null day_code or slot_hour handled without crashing legacy aggregation."""
    c_null_slots = models.Course(
        id=398,
        term_id="2024-2025-1",
        dept_kisaadi="CMPE",
        course_code="CMPE 398",
        section="01",
        title="Independent Study",
        instructor_id=399
    )
    s_null = models.CourseSlot(
        id=398,
        course_id=398,
        day_code=None,
        slot_hour=None,
        room_id=None
    )
    db_session.merge(c_null_slots)
    db_session.merge(s_null)
    db_session.commit()

    res = client.get("/v1/analytics/instructor/399/legacy")
    assert res.status_code == 200
    assert isinstance(res.json()["preferred_slots"], list)


def test_t2_f3_05_instructors_search_sql_wildcards(client: TestClient):
    """Instructors search safely handles SQL wildcards without unconstrained table dump."""
    res = client.get("/v1/instructors?q=%25_")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# ==============================================================================
# TIER 2 - FEATURE 4: Ghost Scheduling & Classroom Heatmap (5 boundary tests)
# ==============================================================================

def test_t2_f4_01_ghost_schedule_nonexistent_term(client: TestClient):
    """Ghost schedule for non-existent term returns empty list."""
    res = client.get("/v1/analytics/ghost-schedule/2099-2100-1")
    assert res.status_code == 200
    assert res.json() == []


def test_t2_f4_02_ghost_schedule_unassigned_rooms(client: TestClient, db_session: Session):
    """Course slots without assigned room (room_id=None) do not crash ghost schedule."""
    c_no_room = models.Course(
        id=499,
        term_id="2024-2025-1",
        dept_kisaadi="CMPE",
        course_code="CMPE 499",
        section="01",
        title="Online Lecture"
    )
    s_no_room = models.CourseSlot(
        id=499,
        course_id=499,
        day_code="F",
        slot_hour=4,
        room_id=None
    )
    db_session.merge(c_no_room)
    db_session.merge(s_no_room)
    db_session.commit()

    res = client.get("/v1/analytics/ghost-schedule/2024-2025-1")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_t2_f4_03_ghost_schedule_nonexistent_dept_filter(client: TestClient):
    """Ghost schedule with non-existent department filter returns empty list."""
    res = client.get("/v1/analytics/ghost-schedule/2024-2025-1?dept=NONEXISTENT")
    assert res.status_code == 200
    assert res.json() == []


def test_t2_f4_04_macro_scheduling_heatmap_out_of_range_decade(client: TestClient):
    """Heatmap query with out-of-range decade returns empty aggregation list."""
    res = client.get("/v1/analytics/macro/scheduling-heatmap?decade=1850")
    assert res.status_code == 200
    assert res.json() == []


def test_t2_f4_05_ghost_schedule_simultaneous_room_conflict(client: TestClient, db_session: Session):
    """Two courses sharing the same room and slot hour are both returned."""
    c_conflict = models.Course(
        id=498,
        term_id="2024-2025-1",
        dept_kisaadi="CMPE",
        course_code="CMPE 498",
        section="02",
        title="Double Booked Lecture"
    )
    s_conflict = models.CourseSlot(
        id=498,
        course_id=498,
        day_code="M",
        slot_hour=1,
        room_id=1
    )
    db_session.merge(c_conflict)
    db_session.merge(s_conflict)
    db_session.commit()

    res = client.get("/v1/analytics/ghost-schedule/2024-2025-1")
    assert res.status_code == 200
    nh101_m1_slots = [
        s for s in res.json()
        if s["room_name"] == "NH101" and s["day_code"] == "M" and s["slot_hour"] == 1
    ]
    assert len(nh101_m1_slots) >= 2


# ==============================================================================
# TIER 2 - FEATURE 5: Quota Tracking & Deduplication (5 boundary tests)
# ==============================================================================

def test_t2_f5_01_course_quota_nonexistent_course(client: TestClient):
    """Querying quota for non-existent course returns empty list."""
    res = client.get("/v1/courses/NONEXISTENT 999/quota")
    assert res.status_code == 200
    assert res.json() == []


def test_t2_f5_02_course_quota_whitespace_trimming(client: TestClient):
    """Padded course code in URL resolves correctly."""
    res = client.get("/v1/courses/%20%20CMPE%20%20150%20%20/quota")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_t2_f5_03_course_quota_unparseable_strings(client: TestClient, db_session: Session):
    """Unparseable quota/current strings parse numeric fields to None."""
    q_corrupt = models.QuotaSnapshot(
        id=599,
        term_id="2024-2025-1",
        course_code="CMPE 599",
        section="01",
        department="CMPE",
        status="Closed",
        quota="TBA",
        current="FULL",
        quota_numeric=None,
        current_numeric=None,
        available=None,
        captured_at="2026-08-28T16:00:00Z"
    )
    db_session.merge(q_corrupt)
    db_session.commit()

    res = client.get("/v1/courses/CMPE 599/quota")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["quota_numeric"] is None
    assert data[0]["current_numeric"] is None


def test_t2_f5_04_course_quota_duplicate_snapshots_same_timestamp(client: TestClient, db_session: Session):
    """Multiple snapshots at same timestamp handled without database conflicts."""
    q_dup = models.QuotaSnapshot(
        id=598,
        term_id="2024-2025-1",
        course_code="CMPE 598",
        section="01",
        department="CMPE",
        status="Open",
        quota="20",
        current="15",
        quota_numeric=20,
        current_numeric=15,
        available=5,
        captured_at="2026-08-28T16:00:00Z"
    )
    db_session.merge(q_dup)
    db_session.commit()

    res = client.get("/v1/courses/CMPE 598/quota?history=true")
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_t2_f5_05_course_quota_empty_code_string(client: TestClient):
    """Empty course code string returns empty list."""
    res = client.get("/v1/courses/%20/quota")
    assert res.status_code == 200
    assert res.json() == []


# ==============================================================================
# TIER 2 - FEATURE 6: Scraper Term & Delta Ingestion (5 boundary tests)
# ==============================================================================

def test_t2_f6_01_sync_deltas_out_of_order_timestamps(db_session: Session):
    """Delta events delivered out-of-order are sorted chronologically."""
    client = MagicMock(spec=ScraperClient)
    client.get.return_value = [
        {
            "change_type": "modified",
            "term": "2024-2025-1",
            "department": "CMPE",
            "course_code": "CMPE 610",
            "section": "01",
            "timestamp": "2026-08-30T15:00:00Z",
            "new_value": {"title": "Advanced Topics - Step 2"}
        },
        {
            "change_type": "added",
            "term": "2024-2025-1",
            "department": "CMPE",
            "course_code": "CMPE 610",
            "section": "01",
            "timestamp": "2026-08-30T10:00:00Z",
            "new_value": {"title": "Advanced Topics - Step 1"}
        }
    ]

    synced = sync_deltas_feed(db_session, client, meili_index=None, limit=100)
    assert synced == 2

    course = db_session.query(models.Course).filter(models.Course.course_code == "CMPE 610").first()
    assert course is not None
    # Latest event timestamp should take final state
    assert course.title == "Advanced Topics - Step 2"


def test_t2_f6_02_sync_deltas_missing_payload_fields(db_session: Session):
    """Delta events with sparse/missing payload fields do not crash ingestion."""
    client = MagicMock(spec=ScraperClient)
    client.get.return_value = [
        {
            "change_type": "added",
            "term": "2024-2025-1",
            "course_code": "CMPE 611",
            "timestamp": "2026-08-30T16:00:00Z",
            "new_value": {}  # completely empty new_value
        }
    ]

    synced = sync_deltas_feed(db_session, client, meili_index=None, limit=100)
    assert synced == 1

    course = db_session.query(models.Course).filter(models.Course.course_code == "CMPE 611").first()
    assert course is not None


def test_t2_f6_03_sync_deltas_remove_nonexistent_course(db_session: Session):
    """Removing non-existent course is a safe no-op."""
    client = MagicMock(spec=ScraperClient)
    client.get.return_value = [
        {
            "change_type": "removed",
            "term": "2024-2025-1",
            "course_code": "GHOST 999",
            "section": "01",
            "timestamp": "2026-08-30T17:00:00Z"
        }
    ]

    synced = sync_deltas_feed(db_session, client, meili_index=None, limit=100)
    assert synced == 1


def test_t2_f6_04_sync_deltas_empty_and_null_responses(db_session: Session):
    """Scraper client returning empty or None list handled cleanly."""
    client = MagicMock(spec=ScraperClient)
    client.get.return_value = []
    synced = sync_deltas_feed(db_session, client, meili_index=None)
    assert synced == 0

    client.get.return_value = None
    synced_none = sync_deltas_feed(db_session, client, meili_index=None)
    assert synced_none == 0


def test_t2_f6_05_sync_quota_feed_missing_term_or_code(db_session: Session):
    """Quota snapshots missing term or course_code are skipped safely."""
    client = MagicMock(spec=ScraperClient)
    client.get.return_value = [
        {"quota": 50},  # Missing term and code
        {"term": "2024-2025-1"},  # Missing code
        {"course_code": "CMPE 150"}  # Missing term
    ]

    synced = sync_quota_feed(db_session, client, limit=100)
    assert synced == 0


# ==============================================================================
# TIER 2 - FEATURE 7: Scraper Idempotent Backfills (5 boundary tests)
# ==============================================================================

def test_t2_f7_01_ensure_term_various_formats(db_session: Session):
    """ensure_term parses academic year and semester number from diverse formats."""
    t1 = ensure_term(db_session, "2028/2029-2")
    assert t1.academic_year == "2028/2029"
    assert t1.semester_num == 2

    t2 = ensure_term(db_session, "2031-3")
    assert t2.academic_year == "2031"
    assert t2.semester_num == 3

    t3 = ensure_term(db_session, "2035")
    assert t3.academic_year == "2035"
    assert t3.semester_num == 1


def test_t2_f7_02_backfill_term_http_error_resilience(db_session: Session):
    """backfill_term catches HTTP errors and aborts without corrupting DB."""
    client = MagicMock(spec=ScraperClient)
    client.get.side_effect = Exception("500 Internal Server Error")

    count = backfill_term(db_session, client, term_id="2025-2026-1")
    assert count == 0


def test_t2_f7_03_backfill_term_empty_courses_list(db_session: Session):
    """backfill_term with empty courses list returns 0."""
    client = MagicMock(spec=ScraperClient)
    client.get.return_value = []

    count = backfill_term(db_session, client, term_id="2025-2026-1")
    assert count == 0


def test_t2_f7_04_clean_int_utility_boundary_values():
    """clean_int handles floats, numeric strings, whitespaces, Nones, invalid values."""
    assert clean_int(10) == 10
    assert clean_int(" 42 ") == 42
    assert clean_int(3.14) == 3
    assert clean_int(None) is None
    assert clean_int("") is None
    assert clean_int("   ") is None
    assert clean_int("not_a_number") is None
    assert clean_int(1000000000) == 1000000000


def test_t2_f7_05_normalize_code_and_section_boundary():
    """normalize_code and normalize_section boundary normalizations."""
    assert normalize_code(" cmpe  150 ") == "CMPE 150"
    assert normalize_code(None) is None
    assert normalize_code("") is None

    assert normalize_section(" 01 ") == "01"
    assert normalize_section(1) == "1"
    assert normalize_section(None) is None
    assert normalize_section("") is None


# ==============================================================================
# TIER 2 - FEATURE 8: Meilisearch Ingestion & Pruning (5 boundary tests)
# ==============================================================================

def test_t2_f8_01_meili_filter_escaping_special_chars():
    """escape_meili_filter handles single quotes and backslashes."""
    escaped_quote = escape_meili_filter("O'Connor")
    assert escaped_quote == "O\\'Connor"

    escaped_bs = escape_meili_filter("Path\\With\\Backslash")
    assert escaped_bs == "Path\\\\With\\\\Backslash"

    escaped_inj = escape_meili_filter("' OR '1'='1")
    assert escaped_inj == "\\' OR \\'1\\'=\\'1"


def test_t2_f8_02_meili_delete_document_exception_handling(db_session: Session):
    """_apply_delta_event handles Meilisearch delete exceptions without breaking DB session."""
    c_mock = models.Course(
        id=899,
        term_id="2024-2025-1",
        dept_kisaadi="CMPE",
        course_code="CMPE 899",
        section="01",
        title="Delete Test"
    )
    db_session.merge(c_mock)
    db_session.commit()

    mock_meili = MagicMock()
    mock_meili.delete_document.side_effect = Exception("Meilisearch node down")

    _apply_delta_event(
        session=db_session,
        item={
            "change_type": "removed",
            "term": "2024-2025-1",
            "course_code": "CMPE 899",
            "section": "01",
            "timestamp": "2026-08-30T18:00:00Z"
        },
        inst_cache={},
        room_cache={},
        dept_cache={},
        term_cache=set(),
        touched_course_ids=set(),
        meili_index=mock_meili,
        dry_run=False
    )

    # Course was removed in DB despite Meilisearch exception
    deleted = db_session.query(models.Course).filter(models.Course.id == 899).first()
    assert deleted is None


def test_t2_f8_03_sync_meili_documents_with_none_index(db_session: Session):
    """sync_meili_documents with index=None is a clean no-op."""
    courses = db_session.query(models.Course).all()
    # Should not raise any error
    sync_meili_documents(None, courses)


def test_t2_f8_04_sync_meili_documents_empty_courses():
    """sync_meili_documents with empty courses list is a clean no-op."""
    mock_index = MagicMock()
    sync_meili_documents(mock_index, [])
    mock_index.add_documents.assert_not_called()


def test_t2_f8_05_facets_fallback_when_meili_unavailable(client: TestClient, monkeypatch):
    """get_global_facets falls back to DB facets when Meilisearch raises exception."""
    mock_meili_client = MagicMock()
    mock_index = MagicMock()
    mock_index.search.side_effect = Exception("Meili timeout")
    mock_meili_client.index.return_value = mock_index

    from app import main
    monkeypatch.setattr(main, "MEILI_CLIENT", mock_meili_client)

    res = client.get("/v1/facets")
    assert res.status_code == 200
    data = res.json()
    assert "term" in data
    assert "dept_code" in data


# ==============================================================================
# TIER 2 - FEATURE 9: Course Change Logs & System Status (5 boundary tests)
# ==============================================================================

def test_t2_f9_01_course_history_nonexistent_course_404(client: TestClient):
    """Non-existent course code returns 404 Not Found in history endpoint."""
    res = client.get("/v1/courses/history/NONEXISTENT 9999")
    assert res.status_code == 404
    assert res.json()["detail"] == "Course history not found"


def test_t2_f9_02_course_history_no_spaces_lookup(client: TestClient):
    """Course history lookup without spaces (e.g. CMPE150) resolves course."""
    res = client.get("/v1/courses/history/CMPE150")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1


def test_t2_f9_03_course_changes_empty_for_unknown_course(client: TestClient):
    """Unknown course returns empty array in /changes without 404/500."""
    res = client.get("/v1/courses/UNKNOWN 9999/changes")
    assert res.status_code == 200
    assert res.json() == []


def test_t2_f9_04_system_status_empty_sync_state_fallback(client: TestClient, db_session: Session):
    """System status succeeds even when SyncState table is completely empty."""
    # Delete all SyncState rows
    db_session.query(models.SyncState).delete()
    db_session.commit()

    res = client.get("/v1/system/status")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "feeds" in data


def test_t2_f9_05_system_status_iso_timestamps(client: TestClient, db_session: Session):
    """System status parses diverse ISO timestamp formats with offsets."""
    state = models.SyncState(feed_name="upstream_run", last_cursor="2026-08-31T10:00:00+00:00")
    db_session.merge(state)
    db_session.commit()

    res = client.get("/v1/system/status")
    assert res.status_code == 200
    data = res.json()
    assert data["last_scraped_at"] == "2026-08-31T10:00:00+00:00"
