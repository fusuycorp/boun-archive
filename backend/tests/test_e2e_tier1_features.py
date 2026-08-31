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
    sync_terms_and_new_offerings,
    _fetch_term_courses,
    sync_meili_documents,
)


# ==============================================================================
# TIER 1 - FEATURE 1: Course Search & Fallback (5 tests)
# ==============================================================================

def test_t1_f1_01_search_by_keyword_course_code(client: TestClient, db_session: Session):
    """Search by course_code with spacing and without spacing."""
    res_space = client.get("/v1/search?q=CMPE%20150")
    assert res_space.status_code == 200
    data = res_space.json()
    assert "hits" in data
    assert any(h["course_code"] == "CMPE 150" for h in data["hits"])

    res_nospace = client.get("/v1/search?q=CMPE150")
    assert res_nospace.status_code == 200
    data_nospace = res_nospace.json()
    assert any(h["course_code"] == "CMPE 150" for h in data_nospace["hits"])


def test_t1_f1_02_search_by_keyword_title(client: TestClient, db_session: Session):
    """Search by course title substring."""
    res = client.get("/v1/search?q=Introduction")
    assert res.status_code == 200
    data = res.json()
    assert len(data["hits"]) >= 1
    assert "Introduction to Computing" in data["hits"][0]["title"]


def test_t1_f1_03_search_by_term_filter(client: TestClient, db_session: Session):
    """Search filtering by term."""
    res = client.get("/v1/search?term=2024-2025-1")
    assert res.status_code == 200
    data = res.json()
    assert len(data["hits"]) >= 1
    assert all(h["term"] == "2024-2025-1" for h in data["hits"])


def test_t1_f1_04_search_by_department_filter(client: TestClient, db_session: Session):
    """Search filtering by department code."""
    res = client.get("/v1/search?dept=CMPE")
    assert res.status_code == 200
    data = res.json()
    assert len(data["hits"]) >= 1
    assert all(h["dept_code"] == "CMPE" for h in data["hits"])


def test_t1_f1_05_search_sorting_and_pagination(client: TestClient, db_session: Session):
    """Search with sorting by credits/course_code and pagination."""
    res = client.get("/v1/search?sort_by=credits&sort_order=desc&limit=1&offset=0")
    assert res.status_code == 200
    data = res.json()
    assert data["limit"] == 1
    assert data["offset"] == 0
    assert len(data["hits"]) == 1


# ==============================================================================
# TIER 1 - FEATURE 2: Department Analytics & Evolution (5 tests)
# ==============================================================================

def test_t1_f2_01_departments_list(client: TestClient):
    """GET /v1/departments returns valid department schemas."""
    res = client.get("/v1/departments")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert any(d["kisaadi"] == "CMPE" for d in data)


def test_t1_f2_02_department_unique_courses_aggregation(client: TestClient, db_session: Session):
    """GET /v1/departments/{dept}/unique-courses groups terms for distinct courses."""
    # Seed an additional offering of CMPE 150 in another term
    term2 = models.Term(id="2023-2024-2", academic_year="2023-2024", semester_num=2)
    c2 = models.Course(
        id=202,
        term_id="2023-2024-2",
        dept_kisaadi="CMPE",
        course_code="CMPE 150",
        section="01",
        title="Introduction to Computing",
        instructor_id=1,
        credits=3,
        ects=6
    )
    db_session.merge(term2)
    db_session.merge(c2)
    db_session.commit()

    res = client.get("/v1/departments/CMPE/unique-courses")
    assert res.status_code == 200
    data = res.json()
    cmpe150 = next((c for c in data if c["course_code"] == "CMPE 150"), None)
    assert cmpe150 is not None
    assert "2024-2025-1" in cmpe150["terms"]
    assert "2023-2024-2" in cmpe150["terms"]


def test_t1_f2_03_department_instructors_metrics(client: TestClient, db_session: Session):
    """GET /v1/departments/{dept}/instructors returns metrics."""
    res = client.get("/v1/departments/CMPE/instructors")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    inst = next((i for i in data if i["full_name"] == "Albert Long"), None)
    assert inst is not None
    assert inst["course_count"] >= 1
    assert inst["total_semesters"] >= 1
    assert inst["last_term"] is not None


def test_t1_f2_04_department_evolution_macro_analytics(client: TestClient, db_session: Session):
    """GET /v1/analytics/macro/departments-evolution returns yearly course counts."""
    res = client.get("/v1/analytics/macro/departments-evolution")
    assert res.status_code == 200
    data = res.json()
    assert "years" in data
    assert "departments" in data
    assert "CMPE" in data["departments"]
    assert len(data["years"]) >= 1


def test_t1_f2_05_department_unique_courses_alphabetical_order(client: TestClient, db_session: Session):
    """Unique courses are returned in alphabetical order by course code."""
    c_extra = models.Course(
        id=203,
        term_id="2024-2025-1",
        dept_kisaadi="CMPE",
        course_code="CMPE 160",
        section="01",
        title="Intro to OOP",
        instructor_id=1,
        credits=3,
        ects=6
    )
    db_session.merge(c_extra)
    db_session.commit()

    res = client.get("/v1/departments/CMPE/unique-courses")
    assert res.status_code == 200
    codes = [c["course_code"] for c in res.json()]
    assert codes == sorted(codes)


# ==============================================================================
# TIER 1 - FEATURE 3: Instructor Analytics & Legacy (5 tests)
# ==============================================================================

def test_t1_f3_01_instructors_list_filter(client: TestClient):
    """GET /v1/instructors?q=Albert returns matching instructor."""
    res = client.get("/v1/instructors?q=Albert")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert "Albert Long" in data[0]["full_name"]


def test_t1_f3_02_instructor_detail_by_id(client: TestClient):
    """GET /v1/instructors/1 returns instructor details."""
    res = client.get("/v1/instructors/1")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == 1
    assert data["full_name"] == "Albert Long"


def test_t1_f3_03_instructor_legacy_totals(client: TestClient):
    """GET /v1/analytics/instructor/1/legacy returns teaching statistics."""
    res = client.get("/v1/analytics/instructor/1/legacy")
    assert res.status_code == 200
    data = res.json()
    assert data["instructor_name"] == "Albert Long"
    assert data["total_semesters_taught"] >= 1
    assert data["total_courses_taught"] >= 1
    assert isinstance(data["history"], list)


def test_t1_f3_04_instructor_legacy_preferred_slots(client: TestClient):
    """Preferred slots returns day and slot_hour distribution."""
    res = client.get("/v1/analytics/instructor/1/legacy")
    assert res.status_code == 200
    data = res.json()
    assert "preferred_slots" in data
    assert len(data["preferred_slots"]) >= 1
    slot = data["preferred_slots"][0]
    assert "day" in slot
    assert "hour" in slot
    assert "frequency" in slot


def test_t1_f3_05_instructor_legacy_most_frequent_courses(client: TestClient):
    """Most frequent courses contains course codes and frequencies."""
    res = client.get("/v1/analytics/instructor/1/legacy")
    assert res.status_code == 200
    data = res.json()
    assert "most_frequent_courses" in data
    assert "CMPE 150" in data["most_frequent_courses"]
    assert data["most_frequent_courses"]["CMPE 150"] >= 1


# ==============================================================================
# TIER 1 - FEATURE 4: Ghost Scheduling & Classroom Heatmap (5 tests)
# ==============================================================================

def test_t1_f4_01_ghost_schedule_reconstruction(client: TestClient):
    """GET /v1/analytics/ghost-schedule/{term} reconstructs campus room slots."""
    res = client.get("/v1/analytics/ghost-schedule/2024-2025-1")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    entry = data[0]
    assert "day_code" in entry
    assert "slot_hour" in entry
    assert "room_name" in entry
    assert "course_code" in entry
    assert entry["room_name"] == "NH101"


def test_t1_f4_02_ghost_schedule_department_filter(client: TestClient):
    """GET /v1/analytics/ghost-schedule/{term}?dept=CMPE filters by department."""
    res = client.get("/v1/analytics/ghost-schedule/2024-2025-1?dept=CMPE")
    assert res.status_code == 200
    data = res.json()
    assert all(e["dept_kisaadi"] == "CMPE" for e in data)


def test_t1_f4_03_macro_scheduling_heatmap_all(client: TestClient):
    """GET /v1/analytics/macro/scheduling-heatmap returns slot frequency matrix."""
    res = client.get("/v1/analytics/macro/scheduling-heatmap")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    item = data[0]
    assert "day_code" in item
    assert "slot_hour" in item
    assert "count" in item


def test_t1_f4_04_macro_scheduling_heatmap_decade_filter(client: TestClient):
    """GET /v1/analytics/macro/scheduling-heatmap?decade=2020 filters by decade."""
    res = client.get("/v1/analytics/macro/scheduling-heatmap?decade=2020")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_t1_f4_05_ghost_schedule_room_association(client: TestClient, db_session: Session):
    """Ghost schedule accurately joins Room name."""
    res = client.get("/v1/analytics/ghost-schedule/2024-2025-1")
    assert res.status_code == 200
    nh101_slots = [s for s in res.json() if s["room_name"] == "NH101"]
    assert len(nh101_slots) >= 1
    assert nh101_slots[0]["day_code"] == "M"
    assert nh101_slots[0]["slot_hour"] == 1


# ==============================================================================
# TIER 1 - FEATURE 5: Quota Tracking & Deduplication (5 tests)
# ==============================================================================

def test_t1_f5_01_course_quota_latest_snapshot(client: TestClient):
    """GET /v1/courses/{course_code}/quota returns snapshot."""
    res = client.get("/v1/courses/CMPE 150/quota")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["course_code"] == "CMPE 150"
    assert data[0]["section"] == "01"


def test_t1_f5_02_course_quota_history_timeline(client: TestClient, db_session: Session):
    """GET /v1/courses/{course_code}/quota?history=true returns chronological snapshots."""
    # Seed an earlier snapshot
    q_earlier = models.QuotaSnapshot(
        id=501,
        term_id="2024-2025-1",
        course_code="CMPE 150",
        section="01",
        department="CMPE",
        status="Open",
        quota="50",
        current="30",
        quota_numeric=50,
        current_numeric=30,
        available=20,
        captured_at="2026-08-27T12:00:00Z"
    )
    db_session.merge(q_earlier)
    db_session.commit()

    res = client.get("/v1/courses/CMPE 150/quota?history=true")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 2
    # Ensure ordered by captured_at descending
    timestamps = [s["captured_at"] for s in data]
    assert timestamps == sorted(timestamps, reverse=True)


def test_t1_f5_03_course_quota_term_filter(client: TestClient):
    """GET /v1/courses/{course_code}/quota?term=2024-2025-1 filters by term."""
    res = client.get("/v1/courses/CMPE 150/quota?term=2024-2025-1")
    assert res.status_code == 200
    data = res.json()
    assert all(s["term_id"] == "2024-2025-1" for s in data)


def test_t1_f5_04_course_quota_numeric_fields(client: TestClient):
    """Quota snapshots contain clean numeric parsed fields."""
    res = client.get("/v1/courses/CMPE 150/quota")
    assert res.status_code == 200
    data = res.json()
    snap = data[0]
    assert snap["quota_numeric"] == 50
    assert snap["current_numeric"] in (45, 30)
    assert snap["available"] is not None


def test_t1_f5_05_course_quota_flags_consent_unlimited(client: TestClient, db_session: Session):
    """Quota snapshots include boolean flags for consent and unlimited."""
    q_consent = models.QuotaSnapshot(
        id=502,
        term_id="2024-2025-1",
        course_code="CMPE 492",
        section="01",
        department="CMPE",
        status="Consent Required",
        quota="Consent",
        current="10",
        quota_numeric=None,
        current_numeric=10,
        is_consent=True,
        is_unlimited=False,
        available=None,
        captured_at="2026-08-28T14:00:00Z"
    )
    db_session.merge(q_consent)
    db_session.commit()

    res = client.get("/v1/courses/CMPE 492/quota")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["is_consent"] is True
    assert data[0]["is_unlimited"] is False


# ==============================================================================
# TIER 1 - FEATURE 6: Scraper Term & Delta Ingestion (5 tests)
# ==============================================================================

def test_t1_f6_01_sync_quota_feed_ingestion_and_cursor(db_session: Session):
    """sync_quota_feed ingests snapshots and updates SyncState cursor."""
    client = MagicMock(spec=ScraperClient)
    client.get.return_value = [
        {
            "term": "2024-2025-1",
            "course_code": "EE 210",
            "section": "01",
            "department": "EE",
            "status": "Open",
            "quota": "60",
            "current": "55",
            "quota_numeric": 60,
            "current_numeric": 55,
            "available": 5,
            "captured_at": "2026-08-29T10:00:00Z"
        }
    ]

    synced = sync_quota_feed(db_session, client, limit=100)
    assert synced == 1

    quota = db_session.query(models.QuotaSnapshot).filter(models.QuotaSnapshot.course_code == "EE 210").first()
    assert quota is not None
    assert quota.current_numeric == 55

    sync_state = db_session.query(models.SyncState).filter(models.SyncState.feed_name == "quota_snapshots").first()
    assert sync_state is not None
    assert sync_state.last_cursor == "2026-08-29T10:00:00Z"


def test_t1_f6_02_sync_deltas_feed_added_event(db_session: Session):
    """sync_deltas_feed handles 'added' event creating course and slots."""
    client = MagicMock(spec=ScraperClient)
    client.get.return_value = [
        {
            "change_type": "added",
            "term": "2024-2025-1",
            "department": "MATH",
            "course_code": "MATH 101",
            "section": "01",
            "timestamp": "2026-08-29T11:00:00Z",
            "new_value": {
                "title": "Calculus I",
                "instructor": "John Nash",
                "credits": 4,
                "ects": 7,
                "delivery_method": "Face-to-Face",
                "slots": [{"day": "T", "hour": 2, "room": "M1100"}]
            },
            "details": "New offering added"
        }
    ]

    synced = sync_deltas_feed(db_session, client, meili_index=None, limit=100)
    assert synced == 1

    course = db_session.query(models.Course).filter(models.Course.course_code == "MATH 101").first()
    assert course is not None
    assert course.title == "Calculus I"
    assert len(course.slots) == 1
    assert course.slots[0].day_code == "T"


def test_t1_f6_03_sync_deltas_feed_modified_event(db_session: Session):
    """sync_deltas_feed handles 'modified' event updating existing course."""
    client = MagicMock(spec=ScraperClient)
    client.get.return_value = [
        {
            "change_type": "modified",
            "term": "2024-2025-1",
            "department": "CMPE",
            "course_code": "CMPE 150",
            "section": "01",
            "timestamp": "2026-08-29T12:00:00Z",
            "old_value": {"credits": 3},
            "new_value": {
                "title": "Intro to Computing (Updated)",
                "credits": 4,
                "ects": 7
            },
            "details": "Credits increased"
        }
    ]

    synced = sync_deltas_feed(db_session, client, meili_index=None, limit=100)
    assert synced == 1

    course = db_session.query(models.Course).filter(models.Course.course_code == "CMPE 150", models.Course.term_id == "2024-2025-1").first()
    assert course.title == "Intro to Computing (Updated)"
    assert course.credits == 4


def test_t1_f6_04_sync_deltas_feed_removed_event(db_session: Session):
    """sync_deltas_feed handles 'removed' event deleting course from DB."""
    # Seed course to be removed
    c_del = models.Course(
        id=601,
        term_id="2024-2025-1",
        dept_kisaadi="CMPE",
        course_code="CMPE 999",
        section="01",
        title="Obsolete Course"
    )
    db_session.merge(c_del)
    db_session.commit()

    client = MagicMock(spec=ScraperClient)
    client.get.return_value = [
        {
            "change_type": "removed",
            "term": "2024-2025-1",
            "department": "CMPE",
            "course_code": "CMPE 999",
            "section": "01",
            "timestamp": "2026-08-29T13:00:00Z",
            "details": "Cancelled course section"
        }
    ]

    synced = sync_deltas_feed(db_session, client, meili_index=None, limit=100)
    assert synced == 1

    removed_course = db_session.query(models.Course).filter(models.Course.course_code == "CMPE 999").first()
    assert removed_course is None


def test_t1_f6_05_sync_deltas_feed_records_changelog(db_session: Session):
    """sync_deltas_feed persists CourseChange audit records."""
    client = MagicMock(spec=ScraperClient)
    client.get.return_value = [
        {
            "change_type": "modified",
            "term": "2024-2025-1",
            "department": "CMPE",
            "course_code": "CMPE 150",
            "section": "01",
            "timestamp": "2026-08-29T14:00:00Z",
            "old_value": {"instructor": "Albert Long"},
            "new_value": {"instructor": "New Instructor"},
            "details": "Instructor handover"
        }
    ]

    sync_deltas_feed(db_session, client, meili_index=None, limit=100)
    change = db_session.query(models.CourseChange).filter(models.CourseChange.timestamp == "2026-08-29T14:00:00Z").first()
    assert change is not None
    assert change.change_type == "modified"
    assert change.details == "Instructor handover"


# ==============================================================================
# TIER 1 - FEATURE 7: Scraper Idempotent Backfills (5 tests)
# ==============================================================================

def test_t1_f7_01_backfill_term_populates_courses(db_session: Session):
    """backfill_term inserts courses, rooms, instructors."""
    client = MagicMock(spec=ScraperClient)
    client.get.return_value = [
        {
            "course_code": "PHYS 101",
            "section": "01",
            "department": "PHYS",
            "course_name": "Physics I",
            "instructor": "Isaac Newton",
            "credits": 4,
            "ects": 6,
            "slots": [{"day": "W", "hour": 3, "room": "KB433"}]
        }
    ]

    count = backfill_term(db_session, client, term_id="2025-2026-1")
    assert count == 1

    phys = db_session.query(models.Course).filter(models.Course.course_code == "PHYS 101").first()
    assert phys is not None
    assert phys.department.bolum == "PHYS"
    assert phys.instructor.full_name == "Isaac Newton"
    assert phys.slots[0].room.name == "KB433"


def test_t1_f7_02_backfill_term_idempotency(db_session: Session):
    """Running backfill_term multiple times on identical payload creates 0 duplicate rows."""
    client = MagicMock(spec=ScraperClient)
    client.get.return_value = [
        {
            "course_code": "PHYS 101",
            "section": "01",
            "department": "PHYS",
            "course_name": "Physics I",
            "instructor": "Isaac Newton",
            "credits": 4,
            "ects": 6,
            "slots": [{"day": "W", "hour": 3, "room": "KB433"}]
        }
    ]

    backfill_term(db_session, client, term_id="2025-2026-1")
    backfill_term(db_session, client, term_id="2025-2026-1")

    phys_count = db_session.query(models.Course).filter(
        models.Course.course_code == "PHYS 101",
        models.Course.term_id == "2025-2026-1"
    ).count()
    assert phys_count == 1


def test_t1_f7_03_ensure_entity_caching(db_session: Session):
    """ensure_term, ensure_department, ensure_instructor, ensure_room use local caches."""
    term_cache = set()
    t1 = ensure_term(db_session, "2027-2028-1", term_cache)
    t2 = ensure_term(db_session, "2027-2028-1", term_cache)
    assert t1.id == t2.id
    assert "2027-2028-1" in term_cache

    inst_cache = {}
    i1 = ensure_instructor(db_session, "Ada Lovelace", inst_cache)
    i2 = ensure_instructor(db_session, "Ada Lovelace", inst_cache)
    assert i1 == i2
    assert "Ada Lovelace" in inst_cache

    room_cache = {}
    r1 = ensure_room(db_session, "M2180", room_cache)
    r2 = ensure_room(db_session, "M2180", room_cache)
    assert r1 == r2
    assert "M2180" in room_cache


def test_t1_f7_04_sync_terms_and_new_offerings_automatic_backfill(db_session: Session):
    """sync_terms_and_new_offerings detects new terms with 0 local courses and triggers backfill."""
    client = MagicMock(spec=ScraperClient)
    def mock_get(path, params=None):
        if path == "terms":
            return ["2029-2030-1"]
        if "feeds/exports" in path or path == "courses":
            return [
                {
                    "course_code": "BIO 101",
                    "section": "01",
                    "department": "BIO",
                    "course_name": "General Biology",
                    "instructor": "Charles Darwin",
                    "credits": 3,
                    "ects": 5,
                    "slots": []
                }
            ]
        return []

    client.get.side_effect = mock_get
    synced_courses = sync_terms_and_new_offerings(db_session, client)
    assert synced_courses == 1

    bio = db_session.query(models.Course).filter(models.Course.course_code == "BIO 101").first()
    assert bio is not None
    assert bio.term_id == "2029-2030-1"


def test_t1_f7_05_fetch_term_courses_export_fallback(db_session: Session):
    """_fetch_term_courses falls back to /courses pagination when export feed is missing."""
    client = MagicMock(spec=ScraperClient)
    def mock_get(path, params=None):
        if "feeds/exports" in path:
            raise Exception("Export not found 404")
        if path == "courses":
            return {
                "items": [{"course_code": "CHEM 101", "section": "01", "course_name": "General Chemistry"}],
                "total": 1
            }
        return []

    client.get.side_effect = mock_get
    courses = _fetch_term_courses(client, "2025-2026-1")
    assert len(courses) == 1
    assert courses[0]["course_code"] == "CHEM 101"


# ==============================================================================
# TIER 1 - FEATURE 8: Meilisearch Ingestion & Pruning (5 tests)
# ==============================================================================

def test_t1_f8_01_sync_meili_documents_formatting(db_session: Session):
    """sync_meili_documents correctly packages courses into documents."""
    mock_index = MagicMock()
    courses = db_session.query(models.Course).filter(models.Course.course_code == "CMPE 150").all()
    
    sync_meili_documents(mock_index, courses, chunk_size=10)
    mock_index.add_documents.assert_called_once()
    
    docs = mock_index.add_documents.call_args[0][0]
    assert len(docs) >= 1
    doc = docs[0]
    assert doc["course_code"] == "CMPE 150"
    assert "slots" in doc
    assert "instructor" in doc


def test_t1_f8_02_apply_delta_event_prunes_meili_document(db_session: Session):
    """_apply_delta_event calls delete_document on 'removed' change_type."""
    c_prune = models.Course(
        id=801,
        term_id="2024-2025-1",
        dept_kisaadi="CMPE",
        course_code="CMPE 888",
        section="01",
        title="Course to Prune"
    )
    db_session.merge(c_prune)
    db_session.commit()

    mock_meili = MagicMock()
    delta_item = {
        "change_type": "removed",
        "term": "2024-2025-1",
        "department": "CMPE",
        "course_code": "CMPE 888",
        "section": "01",
        "timestamp": "2026-08-29T15:00:00Z"
    }

    _apply_delta_event(
        session=db_session,
        item=delta_item,
        inst_cache={},
        room_cache={},
        dept_cache={},
        term_cache=set(),
        touched_course_ids=set(),
        meili_index=mock_meili,
        dry_run=False
    )

    mock_meili.delete_document.assert_called_once_with(801)


def test_t1_f8_03_sync_deltas_feed_updates_meili_index(db_session: Session):
    """sync_deltas_feed pushes touched courses to meili_index."""
    mock_meili = MagicMock()
    client = MagicMock(spec=ScraperClient)
    client.get.return_value = [
        {
            "change_type": "added",
            "term": "2024-2025-1",
            "department": "IE",
            "course_code": "IE 201",
            "section": "01",
            "timestamp": "2026-08-29T16:00:00Z",
            "new_value": {
                "title": "Intro to IE",
                "instructor": "John Doe",
                "credits": 3,
                "ects": 5,
                "slots": []
            }
        }
    ]

    sync_deltas_feed(db_session, client, meili_index=mock_meili, limit=100)
    mock_meili.add_documents.assert_called_once()
    added_docs = mock_meili.add_documents.call_args[0][0]
    assert any(d["course_code"] == "IE 201" for d in added_docs)


def test_t1_f8_04_search_uses_meilisearch_when_available(client: TestClient, monkeypatch):
    """search_courses returns hits directly when Meilisearch responds."""
    mock_meili_client = MagicMock()
    mock_index = MagicMock()
    mock_index.search.return_value = {
        "hits": [
            {
                "id": 999,
                "course_code": "MEILI 101",
                "title": "Fast Search",
                "section": "01",
                "term": "2024-2025-1",
                "department": "Computer Engineering",
                "dept_code": "CMPE",
                "instructor": "Speedy",
                "credits": 3,
                "ects": 5,
                "slots": []
            }
        ],
        "offset": 0,
        "limit": 20,
        "estimatedTotalHits": 1
    }
    mock_meili_client.index.return_value = mock_index

    from app import main
    monkeypatch.setattr(main, "MEILI_CLIENT", mock_meili_client)

    res = client.get("/v1/search?q=MEILI")
    assert res.status_code == 200
    data = res.json()
    assert len(data["hits"]) == 1
    assert data["hits"][0]["course_code"] == "MEILI 101"


def test_t1_f8_05_search_fallback_to_db_on_meili_error(client: TestClient, monkeypatch):
    """search_courses falls back to DB search when Meilisearch raises an exception."""
    mock_meili_client = MagicMock()
    mock_index = MagicMock()
    mock_index.search.side_effect = Exception("Meilisearch down")
    mock_meili_client.index.return_value = mock_index

    from app import main
    monkeypatch.setattr(main, "MEILI_CLIENT", mock_meili_client)

    res = client.get("/v1/search?q=CMPE%20150")
    assert res.status_code == 200
    data = res.json()
    assert len(data["hits"]) >= 1
    assert data["hits"][0]["course_code"] == "CMPE 150"


# ==============================================================================
# TIER 1 - FEATURE 9: Course Change Logs & System Status (5 tests)
# ==============================================================================

def test_t1_f9_01_course_changes_endpoint(client: TestClient):
    """GET /v1/courses/{course_code}/changes returns change log history."""
    res = client.get("/v1/courses/CMPE 150/changes")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["course_code"] == "CMPE 150"
    assert "change_type" in data[0]


def test_t1_f9_02_course_changes_pagination_limit(client: TestClient, db_session: Session):
    """GET /v1/courses/{course_code}/changes?limit=1 limits results."""
    res = client.get("/v1/courses/CMPE 150/changes?limit=1")
    assert res.status_code == 200
    data = res.json()
    assert len(data) <= 1


def test_t1_f9_03_system_status_endpoint(client: TestClient):
    """GET /v1/system/status returns system feeds and health metrics."""
    res = client.get("/v1/system/status")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "feeds" in data
    assert "is_stale" in data


def test_t1_f9_04_system_status_staleness_calculation(client: TestClient, db_session: Session):
    """system/status calculates is_stale appropriately based on timestamp age."""
    res = client.get("/v1/system/status")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data["is_stale"], bool)


def test_t1_f9_05_course_history_multi_term(client: TestClient, db_session: Session):
    """GET /v1/courses/history/{course_code} returns offerings across terms."""
    res = client.get("/v1/courses/history/CMPE 150")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "Intro" in data[0]["title"]
