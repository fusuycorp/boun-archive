import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

from app.main import app
from app.database import Base, get_db
from app import models
from scripts.sync_from_scraper import _upsert_course, _apply_delta_event, sync_quota_feed, ScraperClient


@pytest.fixture
def isolated_boundary_env():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestingSession() as db:
        term = models.Term(id="2026/2027-1", academic_year="2026/2027", semester_num=1)
        dept = models.Department(kisaadi="MIS", bolum="MANAGEMENT INFORMATION SYSTEMS")
        inst = models.Instructor(id=1, full_name="Birgül Kutlu")
        room = models.Room(id=1, name="NH 101", building="New Hall", capacity=100)
        course = models.Course(
            id=1,
            term_id="2026/2027-1",
            dept_kisaadi="MIS",
            course_code="MIS 101",
            section="01",
            title="INTRODUCTION TO MANAGEMENT INFORMATION SYSTEMS",
            instructor_id=1,
            credits=3,
            ects=5,
            delivery_method="In-person"
        )
        slot = models.CourseSlot(
            course_id=1,
            day_code="M",
            slot_hour=2,
            slot_title="INTRO TO MIS",
            room_id=1
        )
        db.add_all([term, dept, inst, room, course, slot])
        db.commit()

    db_session = TestingSession()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    yield {"client": client, "db": db_session}

    app.dependency_overrides.clear()
    db_session.close()
    Base.metadata.drop_all(bind=engine)


def test_department_endpoint_case_insensitivity(isolated_boundary_env):
    client = isolated_boundary_env["client"]

    # Lowercase 'mis'
    res_unique = client.get("/v1/departments/mis/unique-courses")
    assert res_unique.status_code == 200
    data_unique = res_unique.json()
    assert len(data_unique) == 1
    assert data_unique[0]["course_code"] == "MIS 101"

    # Uppercase 'MIS'
    res_unique_upper = client.get("/v1/departments/MIS/unique-courses")
    assert res_unique_upper.status_code == 200
    assert len(res_unique_upper.json()) == 1

    # Instructors endpoint with lowercase 'mis'
    res_inst = client.get("/v1/departments/mis/instructors")
    assert res_inst.status_code == 200
    assert len(res_inst.json()) == 1
    assert res_inst.json()[0]["full_name"] == "Birgül Kutlu"


def test_ghost_schedule_term_format_flexibility(isolated_boundary_env):
    client = isolated_boundary_env["client"]

    # Slash term
    res_slash = client.get("/v1/analytics/ghost-schedule/2026/2027-1")
    assert res_slash.status_code == 200
    assert len(res_slash.json()) == 1

    # Hyphen term
    res_dash = client.get("/v1/analytics/ghost-schedule/2026-2027-1")
    assert res_dash.status_code == 200
    assert len(res_dash.json()) == 1

    # Lowercase dept query param
    res_dept = client.get("/v1/analytics/ghost-schedule/2026/2027-1?dept=mis")
    assert res_dept.status_code == 200
    assert len(res_dept.json()) == 1


def test_scraper_upsert_normalizes_lowercase_department(isolated_boundary_env):
    db_session = isolated_boundary_env["db"]

    course = _upsert_course(
        session=db_session,
        term_id="2026/2027-1",
        dept_kisaadi="mis",
        course_code="MIS 211",
        section="01",
        val_payload={"title": "BUSINESS PROGRAMMING", "credits": 3},
        inst_cache={},
        room_cache={},
        dept_cache={},
        term_cache={}
    )
    db_session.commit()

    assert course is not None
    assert course.dept_kisaadi == "MIS"


def test_scraper_delta_event_normalizes_department(isolated_boundary_env):
    db_session = isolated_boundary_env["db"]
    touched_ids = set()

    delta_item = {
        "change_type": "added",
        "term": "2026/2027-1",
        "department": "mis",
        "course_code": "MIS 450",
        "section": "01",
        "timestamp": "2026-09-01T10:00:00Z",
        "new_value": {
            "title": "ADVANCED MIS",
            "credits": 3
        }
    }

    _apply_delta_event(
        session=db_session,
        item=delta_item,
        inst_cache={},
        room_cache={},
        dept_cache={},
        term_cache={},
        touched_course_ids=touched_ids,
        meili_index=None
    )
    db_session.commit()

    assert len(touched_ids) == 1
    course = db_session.query(models.Course).filter(models.Course.course_code == "MIS 450").first()
    assert course is not None
    assert course.dept_kisaadi == "MIS"


def test_sync_quota_feed_normalizes_department(isolated_boundary_env):
    db_session = isolated_boundary_env["db"]
    mock_client = MagicMock(spec=ScraperClient)
    mock_client.get.return_value = [
        {
            "term": "2026/2027-1",
            "course_code": "MIS 101",
            "section": "01",
            "department": "mis",
            "status": "Open",
            "quota": "50",
            "current": "20",
            "quota_numeric": 50,
            "current_numeric": 20,
            "available": 30,
            "captured_at": "2026-09-01T12:00:00Z"
        }
    ]

    synced = sync_quota_feed(db_session, mock_client, limit=10)
    db_session.commit()

    quota = db_session.query(models.QuotaSnapshot).filter(
        models.QuotaSnapshot.course_code == "MIS 101",
        models.QuotaSnapshot.section == "01"
    ).first()
    assert quota is not None
    assert quota.department == "MIS"
