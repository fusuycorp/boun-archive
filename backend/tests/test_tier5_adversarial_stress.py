"""
Tier 5 Adversarial & Stress Testing Suite for BOUN Archive & Scraper Ingestion Pipeline.

Coverage Areas:
1. SQL Injection & Filter Injection Stress
2. Zero-Hit Searches & Meilisearch Fallback Resilience
3. Scraper Term Parsing with Diverse & Unusual Formats
4. Quota Snapshot Deduplication Under High-Frequency Polling
5. Delta Sync Events with Out-of-Order Timestamps & Mixed-Case Verbs
6. Course Upsert with Department Migration & Null Handling
7. High-Volume Ingestion Stress & Macro Analytics Edge Cases
"""

import sys
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import models, schemas
from app.main import app, escape_meili_filter, escape_sql_wildcards, _search_courses_from_db, _get_global_facets_from_db
from app.analytics import MacroEngine
from app.database import Base, get_db
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
    _sync_course_slots,
    sync_quota_feed,
    sync_deltas_feed,
    backfill_term,
    sync_meili_documents,
)


@pytest.fixture
def isolated_db():
    """Create a completely isolated in-memory SQLite database for test runs."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    
    session = TestingSession()
    try:
        # Seed standard baseline entities
        term = models.Term(id="2024-2025-1", academic_year="2024-2025", semester_num=1)
        dept_cmpe = models.Department(kisaadi="CMPE", bolum="Computer Engineering")
        dept_ee = models.Department(kisaadi="EE", bolum="Electrical and Electronics Engineering")
        dept_math = models.Department(kisaadi="MATH", bolum="Mathematics")
        instructor = models.Instructor(id=1, full_name="Albert Long")
        room = models.Room(id=1, name="NH101", building="New Hall", capacity=100)
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
        slot = models.CourseSlot(
            id=1,
            course_id=1,
            day_code="M",
            slot_hour=1,
            slot_title="CMPE 150.01",
            room_id=1
        )
        session.add_all([term, dept_cmpe, dept_ee, dept_math, instructor, room, course, slot])
        session.commit()
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def isolated_client(isolated_db):
    """Create a FastAPI test client connected to the isolated database."""
    def override_get_db():
        try:
            yield isolated_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ==============================================================================
# 1. SQL INJECTION & FILTER INJECTION ADVERSARIAL TESTS
# ==============================================================================

class TestSqlAndFilterInjection:
    """Stress tests verifying SQL injection resilience and wildcard sanitization."""

    SQLI_PAYLOADS = [
        "CMPE' OR '1'='1",
        "CMPE' OR '1'='1' --",
        "'; DROP TABLE courses; --",
        "' UNION SELECT id, term_id, dept_kisaadi, course_code, section, title, instructor_id, credits, ects, delivery_method FROM courses --",
        "CMPE' AND (SELECT count(*) FROM courses) > 0 --",
        "CMPE' OR 1=CAST((SELECT 1) AS int) --",
        "CMPE' OR pg_sleep(5) --",
        "CMPE' AND 1=1/*",
        "CMPE' AND 1=2 UNION ALL SELECT NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL--",
        "%_%_%_%_%_%_%_%_%",
        "\\\\%\\\\_\\\\%\\\\_",
        "CMPE\x00' OR '1'='1",
        "'''\"\"\"--/*",
        "İÖÜŞÇĞ ıüşçğ ' OR '1'='1",
    ]

    def test_search_q_parameter_sqli_payloads(self, isolated_client: TestClient):
        """Verify search q parameter handles hostile SQLi payloads safely."""
        for payload in self.SQLI_PAYLOADS:
            res = isolated_client.get("/v1/search", params={"q": payload})
            assert res.status_code == 200, f"Failed for payload: {payload}"
            data = res.json()
            assert "hits" in data
            assert isinstance(data["hits"], list)

    def test_search_filter_parameters_injection_escaping(self, isolated_client: TestClient):
        """Verify term, dept, and instructor filter inputs are escaped against Meilisearch filter injection."""
        hostile_filters = [
            ("term", "2024-2025-1' OR term = '2024-2025-2"),
            ("dept", "CMPE' OR dept_code != 'CMPE"),
            ("instructor", "Albert Long' OR instructor != 'Albert Long"),
            ("dept", "CMPE\\') OR (1=1"),
            ("term", "2024-2025-1\\'"),
        ]
        for param, val in hostile_filters:
            res = isolated_client.get("/v1/search", params={param: val})
            assert res.status_code == 200, f"Failed on filter {param}={val}"
            data = res.json()
            assert "hits" in data

    def test_direct_endpoints_sqli_resilience(self, isolated_client: TestClient):
        """Verify parameterized queries across all resource endpoints resist SQL injection."""
        endpoints = [
            "/v1/instructors?q=Albert'%20OR%20'1'='1",
            "/v1/courses/history/CMPE%20150'%20OR%20'1'='1'--",
            "/v1/courses/CMPE%20150'%20OR%20'1'='1'/quota",
            "/v1/courses/CMPE%20150'%20OR%20'1'='1'/changes",
            "/v1/departments/CMPE'%20OR%20'1'='1/unique-courses",
            "/v1/departments/CMPE'%20OR%20'1'='1/instructors",
            "/v1/analytics/ghost-schedule/2024-2025-1'%20OR%20'1'='1",
        ]
        for url in endpoints:
            res = isolated_client.get(url)
            # Endpoints must either return 200 with sanitized result, or 404 cleanly, never 500
            assert res.status_code in (200, 404), f"Endpoint crashed with {res.status_code} for {url}"

    def test_wildcard_escaping_behavior(self, isolated_db: Session):
        """Verify escape_sql_wildcards properly escapes %, _, and backslashes."""
        assert escape_sql_wildcards("100%_pure\\code") == "100\\%\\_pure\\\\code"
        assert escape_meili_filter("O'Connor\\Dept") == "O\\'Connor\\\\Dept"


# ==============================================================================
# 2. ZERO-HIT SEARCHES & MEILISEARCH FALLBACK BEHAVIOR
# ==============================================================================

class TestZeroHitAndMeilisearchFallback:
    """Stress tests verifying search resilience under Meilisearch outages and zero hits."""

    def test_legitimate_zero_hit_search_does_not_error(self, isolated_client: TestClient):
        """Zero-hit search returns empty list with totalHits=0 without crashing."""
        res = isolated_client.get("/v1/search", params={"q": "NONEXISTENT_COURSE_CODE_123456789"})
        assert res.status_code == 200
        data = res.json()
        assert data["hits"] == []
        assert data.get("totalHits", 0) == 0

    def test_meilisearch_outage_triggers_transparent_db_fallback(self, isolated_client: TestClient):
        """When Meilisearch raises an exception, the search API cleanly falls back to PostgreSQL."""
        with patch("app.main.MEILI_CLIENT.index") as mock_index:
            mock_index.side_effect = Exception("Meilisearch Cluster Unreachable (503 Service Unavailable)")
            
            res = isolated_client.get("/v1/search", params={"q": "CMPE 150"})
            assert res.status_code == 200
            data = res.json()
            assert "hits" in data
            assert len(data["hits"]) >= 1
            hit = data["hits"][0]
            assert hit["course_code"] == "CMPE 150"
            assert hit["instructor"] == "Albert Long"
            assert "slots" in hit
            assert len(hit["slots"]) == 1
            assert hit["slots"][0]["room_name"] == "NH101"

    def test_db_fallback_search_filtering_and_sorting(self, isolated_db: Session):
        """Verify _search_courses_from_db correctly implements all filters, sorts, and pagination."""
        # Test term filter
        res_term = _search_courses_from_db(
            db=isolated_db,
            q="",
            term=["2024-2025-1"],
            dept=None,
            instructor=None,
            sort_by="course_code",
            sort_order="asc",
            limit=10,
            offset=0
        )
        assert len(res_term["hits"]) == 1
        assert res_term["totalHits"] == 1

        # Test non-matching dept filter
        res_dept = _search_courses_from_db(
            db=isolated_db,
            q="",
            term=None,
            dept=["NONEXISTENT"],
            instructor=None,
            sort_by="course_code",
            sort_order="asc",
            limit=10,
            offset=0
        )
        assert len(res_dept["hits"]) == 0
        assert res_dept["totalHits"] == 0

        # Test instructor filter
        res_inst = _search_courses_from_db(
            db=isolated_db,
            q="",
            term=None,
            dept=None,
            instructor="Albert Long",
            sort_by="title",
            sort_order="desc",
            limit=10,
            offset=0
        )
        assert len(res_inst["hits"]) == 1
        assert res_inst["hits"][0]["instructor"] == "Albert Long"

        # Test spaceless course code search
        res_spaceless = _search_courses_from_db(
            db=isolated_db,
            q="CMPE150",
            term=None,
            dept=None,
            instructor=None,
            sort_by=None,
            sort_order="asc",
            limit=10,
            offset=0
        )
        assert len(res_spaceless["hits"]) == 1
        assert res_spaceless["hits"][0]["course_code"] == "CMPE 150"

    def test_global_facets_fallback_calculation(self, isolated_db: Session):
        """Verify _get_global_facets_from_db extracts aggregated facet distributions from relational store."""
        facets = _get_global_facets_from_db(isolated_db)
        assert "term" in facets
        assert "dept_code" in facets
        assert "delivery_method" in facets
        assert facets["term"].get("2024-2025-1") == 1
        assert facets["dept_code"].get("CMPE") == 1
        assert facets["delivery_method"].get("Face-to-Face") == 1


# ==============================================================================
# 3. SCRAPER TERM PARSING WITH DIVERSE & UNUSUAL FORMATS
# ==============================================================================

class TestScraperTermParsing:
    """Stress tests verifying term format normalization and robust parsing."""

    @pytest.mark.parametrize("term_id, expected_year, expected_sem", [
        ("2024-2025-1", "2024-2025", 1),
        ("2024-2025-2", "2024-2025", 2),
        ("2024-2025-3", "2024-2025", 3),
        ("2024/2025-1", "2024/2025", 1),
        ("2024/2025-2", "2024/2025", 2),
        ("2030-3", "2030", 3),
        ("2028/2029/2", "2028/2029", 2),
        ("2035", "2035", 1),
        ("2024-2025-Summer", "2024-2025", 1),
        ("Fall-2024-2", "Fall-2024", 2),
        ("2024-2025-99", "2024-2025", 99),
        ("2026-2027-0", "2026-2027", 1),
    ])
    def test_ensure_term_parsing_formats(self, isolated_db: Session, term_id: str, expected_year: str, expected_sem: int):
        """Verify ensure_term parses academic year and semester number across various formats."""
        term = ensure_term(isolated_db, term_id)
        assert term.id == term_id
        assert term.academic_year == expected_year
        assert term.semester_num == expected_sem

        # Verify idempotency (querying again does not create duplicate rows)
        term_again = ensure_term(isolated_db, term_id)
        assert term_again.id == term.id

        total_matching_terms = isolated_db.query(models.Term).filter(models.Term.id == term_id).count()
        assert total_matching_terms == 1

    def test_ensure_term_with_cache_variations(self, isolated_db: Session):
        """Verify ensure_term works correctly with set cache, dict cache, or no cache."""
        dict_cache = {}
        t1 = ensure_term(isolated_db, "2027-2028-1", term_cache=dict_cache)
        assert "2027-2028-1" in dict_cache
        t1_cached = ensure_term(isolated_db, "2027-2028-1", term_cache=dict_cache)
        assert t1_cached is t1

        set_cache = set()
        t2 = ensure_term(isolated_db, "2028-2029-1", term_cache=set_cache)
        assert "2028-2029-1" in set_cache
        t2_cached = ensure_term(isolated_db, "2028-2029-1", term_cache=set_cache)
        assert t2_cached.id == "2028-2029-1"


# ==============================================================================
# 4. QUOTA SNAPSHOT DEDUPLICATION UNDER RAPID REPEATED POLLING
# ==============================================================================

class TestQuotaSnapshotDeduplication:
    """Stress tests verifying high-frequency quota snapshot deduplication."""

    def test_rapid_identical_polling_produces_zero_duplicate_rows(self, isolated_db: Session):
        """Repeatedly polling identical quota snapshots updates in place without inserting duplicates."""
        mock_client = MagicMock(spec=ScraperClient)
        
        batch_payload = [
            {
                "term": "2024-2025-1",
                "course_code": "CMPE 150",
                "section": "01",
                "department": "CMPE",
                "status": "Open",
                "quota": "50",
                "current": "45",
                "quota_numeric": 50,
                "current_numeric": 45,
                "available": 5,
                "is_consent": False,
                "is_unlimited": False,
                "captured_at": "2026-08-31T10:00:00Z"
            }
        ]

        # Simulate 10 rapid repeated polling cycles with identical captured_at
        for _ in range(10):
            mock_client.get.return_value = list(batch_payload)
            synced = sync_quota_feed(isolated_db, mock_client, limit=100)
            assert synced == 1

        # Count records in QuotaSnapshot
        count = isolated_db.query(models.QuotaSnapshot).filter(
            models.QuotaSnapshot.course_code == "CMPE 150",
            models.QuotaSnapshot.section == "01",
            models.QuotaSnapshot.captured_at == "2026-08-31T10:00:00Z"
        ).count()
        assert count == 1, f"Expected 1 deduplicated record, found {count}"

    def test_polling_with_shifting_enrollment_and_consent(self, isolated_db: Session):
        """Simulate registration week quota dynamics with enrollment shifts and consent changes."""
        mock_client = MagicMock(spec=ScraperClient)

        waves = [
            {
                "term": "2024-2025-1",
                "course_code": "CMPE 150",
                "section": "01",
                "department": "CMPE",
                "status": "Open",
                "quota": "50",
                "current": "45",
                "captured_at": "2026-08-31T10:00:00Z"
            },
            {
                "term": "2024-2025-1",
                "course_code": "CMPE 150",
                "section": "01",
                "department": "CMPE",
                "status": "Full",
                "quota": "50",
                "current": "50",
                "captured_at": "2026-08-31T10:05:00Z"
            },
            {
                "term": "2024-2025-1",
                "course_code": "CMPE 150",
                "section": "01",
                "department": "CMPE",
                "status": "Consent",
                "quota": "60",
                "current": "50",
                "is_consent": True,
                "captured_at": "2026-08-31T10:10:00Z"
            },
        ]

        for wave in waves:
            mock_client.get.return_value = [wave]
            sync_quota_feed(isolated_db, mock_client, limit=100)

        # Total history snapshots should equal 3 distinct timestamps
        history = isolated_db.query(models.QuotaSnapshot).filter(
            models.QuotaSnapshot.course_code == "CMPE 150",
            models.QuotaSnapshot.section == "01"
        ).order_by(models.QuotaSnapshot.captured_at.asc()).all()

        assert len(history) == 3
        assert history[0].current_numeric == 45
        assert history[1].current_numeric == 50
        assert history[2].is_consent is True
        assert history[2].quota_numeric == 60
        assert history[2].available == 10

    def test_non_numeric_and_malformed_quota_fields(self, isolated_db: Session):
        """Verify non-numeric strings ('TBA', 'Unlimited', negative values) parse safely."""
        mock_client = MagicMock(spec=ScraperClient)
        mock_client.get.return_value = [
            {
                "term": "2024-2025-1",
                "course_code": "CMPE 150",
                "section": "02",
                "department": "ALL",
                "status": "Open",
                "quota": "TBA",
                "current": "Unlimited",
                "quota_numeric": None,
                "current_numeric": None,
                "available": None,
                "is_unlimited": True,
                "captured_at": "2026-08-31T11:00:00Z"
            }
        ]
        sync_quota_feed(isolated_db, mock_client, limit=100)

        snap = isolated_db.query(models.QuotaSnapshot).filter(
            models.QuotaSnapshot.course_code == "CMPE 150",
            models.QuotaSnapshot.section == "02"
        ).first()

        assert snap is not None
        assert snap.quota == "TBA"
        assert snap.current == "Unlimited"
        assert snap.quota_numeric is None
        assert snap.current_numeric is None
        assert snap.is_unlimited is True


# ==============================================================================
# 5. DELTA SYNC EVENTS WITH OUT-OF-ORDER TIMESTAMPS & MIXED-CASE VERBS
# ==============================================================================

class TestDeltaSyncOutOfOrderAndVerbs:
    """Stress tests verifying causal ordering and verb normalization during delta ingestion."""

    def test_mixed_case_and_verb_synonyms(self, isolated_db: Session):
        """Verify mixed-case verbs ('INSERT', 'update', 'UPDATED', 'delete', 'MODIFIED', 'added') execute properly."""
        mock_client = MagicMock(spec=ScraperClient)
        
        # Test INSERT / added
        mock_client.get.return_value = [
            {
                "change_type": "INSERT",
                "term": "2024-2025-1",
                "department": "MATH",
                "course_code": "MATH 101",
                "section": "01",
                "timestamp": "2026-08-31T12:00:00Z",
                "new_value": {
                    "title": "Calculus I",
                    "instructor": "John Nash",
                    "credits": 4,
                    "ects": 7
                }
            }
        ]
        sync_deltas_feed(isolated_db, mock_client, limit=100)

        math_course = isolated_db.query(models.Course).filter(
            models.Course.course_code == "MATH 101",
            models.Course.section == "01"
        ).first()
        assert math_course is not None
        assert math_course.title == "Calculus I"
        assert math_course.credits == 4

        # Test UPDATE / MODIFIED
        mock_client.get.return_value = [
            {
                "change_type": "MODIFIED",
                "term": "2024-2025-1",
                "department": "MATH",
                "course_code": "MATH 101",
                "section": "01",
                "timestamp": "2026-08-31T12:05:00Z",
                "new_value": {
                    "title": "Advanced Calculus I",
                    "credits": 5
                }
            }
        ]
        sync_deltas_feed(isolated_db, mock_client, limit=100)
        isolated_db.refresh(math_course)
        assert math_course.title == "Advanced Calculus I"
        assert math_course.credits == 5

        # Test DELETE / removed
        mock_client.get.return_value = [
            {
                "change_type": "DELETE",
                "term": "2024-2025-1",
                "department": "MATH",
                "course_code": "MATH 101",
                "section": "01",
                "timestamp": "2026-08-31T12:10:00Z"
            }
        ]
        sync_deltas_feed(isolated_db, mock_client, limit=100)
        deleted_course = isolated_db.query(models.Course).filter(
            models.Course.course_code == "MATH 101",
            models.Course.section == "01"
        ).first()
        assert deleted_course is None

    def test_out_of_order_delta_timestamps_replay_causal_order(self, isolated_db: Session):
        """When delta events arrive in scrambled timestamp order, sorting by timestamp ensures correct final state."""
        mock_client = MagicMock(spec=ScraperClient)

        # Scrambled events: t3 arrives before t1 and t2
        scrambled_events = [
            {
                "change_type": "update",
                "term": "2024-2025-1",
                "department": "EE",
                "course_code": "EE 212",
                "section": "01",
                "timestamp": "2026-08-31T14:00:00Z",  # t3: final desired title
                "new_value": {"title": "Circuits Final Version"}
            },
            {
                "change_type": "added",
                "term": "2024-2025-1",
                "department": "EE",
                "course_code": "EE 212",
                "section": "01",
                "timestamp": "2026-08-31T12:00:00Z",  # t1: initial creation
                "new_value": {"title": "Circuits V1", "credits": 3}
            },
            {
                "change_type": "modified",
                "term": "2024-2025-1",
                "department": "EE",
                "course_code": "EE 212",
                "section": "01",
                "timestamp": "2026-08-31T13:00:00Z",  # t2: intermediate update
                "new_value": {"title": "Circuits V2"}
            }
        ]

        mock_client.get.return_value = scrambled_events
        sync_deltas_feed(isolated_db, mock_client, limit=100)

        course = isolated_db.query(models.Course).filter(
            models.Course.course_code == "EE 212",
            models.Course.section == "01"
        ).first()

        assert course is not None
        # Causal reordering MUST produce the state from t3 (Circuits Final Version), NOT t2 or t1
        assert course.title == "Circuits Final Version"
        assert course.credits == 3

        # Verify cursor advanced to t3
        state = isolated_db.query(models.SyncState).filter(models.SyncState.feed_name == "deltas").first()
        assert state is not None
        assert state.last_cursor == "2026-08-31T14:00:00Z"

    def test_out_of_order_delete_and_recreation(self, isolated_db: Session):
        """Scrambled events containing delete and modify resolve in proper chronological sequence."""
        mock_client = MagicMock(spec=ScraperClient)

        # Initial add at t1, modify at t2, delete at t3 - passed in scrambled order [t3, t1, t2]
        events = [
            {
                "change_type": "delete",
                "term": "2024-2025-1",
                "department": "EE",
                "course_code": "EE 499",
                "section": "01",
                "timestamp": "2026-08-31T15:00:00Z"  # t3: deleted
            },
            {
                "change_type": "added",
                "term": "2024-2025-1",
                "department": "EE",
                "course_code": "EE 499",
                "section": "01",
                "timestamp": "2026-08-31T10:00:00Z",  # t1
                "new_value": {"title": "Graduation Project"}
            },
            {
                "change_type": "modified",
                "term": "2024-2025-1",
                "department": "EE",
                "course_code": "EE 499",
                "section": "01",
                "timestamp": "2026-08-31T12:00:00Z",  # t2
                "new_value": {"title": "Senior Design Project"}
            }
        ]

        mock_client.get.return_value = events
        sync_deltas_feed(isolated_db, mock_client, limit=100)

        course = isolated_db.query(models.Course).filter(
            models.Course.course_code == "EE 499",
            models.Course.section == "01"
        ).first()

        # Since t3 is delete, final state MUST be deleted (None)
        assert course is None


# ==============================================================================
# 6. COURSE UPSERT WITH CHANGING DEPARTMENT CODES & NULL DEPARTMENTS
# ==============================================================================

class TestCourseUpsertDepartmentTransitions:
    """Stress tests verifying department updates, null department handling, and slot reconciliation."""

    def test_course_upsert_department_migration(self, isolated_db: Session):
        """A course moving from department CMPE to EE updates dept_kisaadi and foreign key link cleanly."""
        course = _upsert_course(
            session=isolated_db,
            term_id="2024-2025-1",
            dept_kisaadi="CMPE",
            course_code="CS 101",
            section="01",
            val_payload={"title": "Comp Sci", "credits": 3},
            inst_cache={},
            room_cache={},
            dept_cache={},
            term_cache={}
        )
        assert course.dept_kisaadi == "CMPE"

        # Migrate department to EE
        updated_course = _upsert_course(
            session=isolated_db,
            term_id="2024-2025-1",
            dept_kisaadi="EE",
            course_code="CS 101",
            section="01",
            val_payload={"title": "Comp Sci in EE", "credits": 3},
            inst_cache={},
            room_cache={},
            dept_cache={},
            term_cache={}
        )
        assert updated_course.dept_kisaadi == "EE"
        assert updated_course.id == course.id

        # Verify in DB
        db_course = isolated_db.query(models.Course).filter(models.Course.id == course.id).first()
        assert db_course.dept_kisaadi == "EE"
        assert db_course.department.kisaadi == "EE"

    def test_course_upsert_with_null_and_empty_department(self, isolated_db: Session):
        """Upserting a course with null or empty department does not crash or corrupt database state."""
        course = _upsert_course(
            session=isolated_db,
            term_id="2024-2025-1",
            dept_kisaadi=None,
            course_code="GEN 100",
            section="01",
            val_payload={"title": "General Studies", "credits": 1},
            inst_cache={},
            room_cache={},
            dept_cache={},
            term_cache={}
        )
        assert course is not None
        assert course.dept_kisaadi is None

        # Re-upserting with empty string department
        course_empty = _upsert_course(
            session=isolated_db,
            term_id="2024-2025-1",
            dept_kisaadi="",
            course_code="GEN 100",
            section="02",
            val_payload={"title": "General Studies II", "credits": 1},
            inst_cache={},
            room_cache={},
            dept_cache={},
            term_cache={}
        )
        assert course_empty is not None

    def test_course_slots_reconciliation_on_upsert(self, isolated_db: Session):
        """Updating course slots completely reconciles timetable without leaving orphan slot rows."""
        inst_cache = {}
        room_cache = {}
        
        # Initial slots: M1 in NH101, T2 in NH101
        payload_1 = {
            "title": "Robotics",
            "slots": [
                {"day": "M", "hour": 1, "room": "NH101"},
                {"day": "T", "hour": 2, "room": "NH101"}
            ]
        }
        course = _upsert_course(
            session=isolated_db,
            term_id="2024-2025-1",
            dept_kisaadi="CMPE",
            course_code="CMPE 480",
            section="01",
            val_payload=payload_1,
            inst_cache=inst_cache,
            room_cache=room_cache,
            dept_cache={},
            term_cache={}
        )
        isolated_db.flush()

        slots = isolated_db.query(models.CourseSlot).filter(models.CourseSlot.course_id == course.id).all()
        assert len(slots) == 2

        # Shift schedule to W4 in KB202 (single slot)
        payload_2 = {
            "title": "Robotics",
            "slots": [
                {"day": "W", "hour": 4, "room": "KB202"}
            ]
        }
        _upsert_course(
            session=isolated_db,
            term_id="2024-2025-1",
            dept_kisaadi="CMPE",
            course_code="CMPE 480",
            section="01",
            val_payload=payload_2,
            inst_cache=inst_cache,
            room_cache=room_cache,
            dept_cache={},
            term_cache={}
        )
        isolated_db.flush()

        updated_slots = isolated_db.query(models.CourseSlot).filter(models.CourseSlot.course_id == course.id).all()
        assert len(updated_slots) == 1
        assert updated_slots[0].day_code == "W"
        assert updated_slots[0].slot_hour == 4
        assert updated_slots[0].room.name == "KB202"


# ==============================================================================
# 7. HIGH-VOLUME INGESTION STRESS & MACRO ANALYTICS EDGE CASES
# ==============================================================================

class TestHighVolumeAndMacroAnalytics:
    """Stress tests simulating high batch size ingestion and macro analytics aggregations."""

    def test_high_volume_batch_backfill_and_search_indexing(self, isolated_db: Session):
        """Simulate high volume backfill of 100 courses with multiple slots across 5 departments."""
        mock_client = MagicMock(spec=ScraperClient)
        mock_meili = MagicMock()

        bulk_courses = []
        dept_codes = ["CMPE", "EE", "MATH", "PHYS", "CHEM"]
        for d in dept_codes:
            ensure_department(isolated_db, d)

        for i in range(1, 101):
            d = dept_codes[i % len(dept_codes)]
            bulk_courses.append({
                "department": d,
                "course_code": f"{d} {100 + i}",
                "section": "01",
                "title": f"Course Subject {i}",
                "instructor": f"Professor {d} {i % 10}",
                "credits": 3,
                "ects": 6,
                "slots": [
                    {"day": "M", "hour": 1, "room": f"HALL_{i % 5}"},
                    {"day": "Th", "hour": 2, "room": f"HALL_{i % 5}"}
                ]
            })

        mock_client.get.return_value = bulk_courses
        count = backfill_term(
            session=isolated_db,
            client=mock_client,
            meili_index=mock_meili,
            term_id="2025-2026-1"
        )
        assert count == 100

        # Verify Meilisearch sync was called with chunked documents
        assert mock_meili.add_documents.called

        # Total courses in DB for term 2025-2026-1 must equal 100
        db_count = isolated_db.query(models.Course).filter(models.Course.term_id == "2025-2026-1").count()
        assert db_count == 100

        # Total slots created must equal 200
        slot_count = isolated_db.query(models.CourseSlot).join(models.Course).filter(models.Course.term_id == "2025-2026-1").count()
        assert slot_count == 200

    def test_macro_analytics_with_diverse_data(self, isolated_db: Session):
        """Verify MacroEngine handles multi-decade course offerings and slot heatmaps accurately."""
        # Add historical offerings from 2010, 2020, and 2030
        for yr in ["2010", "2020", "2030"]:
            term_id = f"{yr}-{int(yr)+1}-1"
            ensure_term(isolated_db, term_id)
            c = models.Course(
                term_id=term_id,
                dept_kisaadi="CMPE",
                course_code=f"CMPE {yr}",
                section="01",
                title=f"Advanced Computing {yr}"
            )
            isolated_db.add(c)
            isolated_db.flush()
            slot = models.CourseSlot(course_id=c.id, day_code="M", slot_hour=1)
            isolated_db.add(slot)
        isolated_db.commit()

        # Evolution analytics
        evolution = MacroEngine.get_department_evolution(isolated_db)
        assert "years" in evolution
        assert "departments" in evolution
        assert "2010" in evolution["years"]
        assert "2020" in evolution["years"]
        assert "2030" in evolution["years"]

        # Scheduling heatmap with decade filtering
        heatmap_2010 = MacroEngine.get_scheduling_heatmap(isolated_db, decade=2010)
        assert isinstance(heatmap_2010, list)
        assert len(heatmap_2010) >= 1
        assert heatmap_2010[0]["day_code"] == "M"

        # Scheduling heatmap without decade filter (all time)
        heatmap_all = MacroEngine.get_scheduling_heatmap(isolated_db, decade=None)
        assert isinstance(heatmap_all, list)
        assert len(heatmap_all) >= 1
