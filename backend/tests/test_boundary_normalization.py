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
    slash_data = res_slash.json()
    assert len(slash_data) == 1
    assert slash_data[0]["building"] == "New Hall"
    assert slash_data[0]["room_name"] == "NH 101"

    # Hyphen term
    res_dash = client.get("/v1/analytics/ghost-schedule/2026-2027-1")
    assert res_dash.status_code == 200
    assert len(res_dash.json()) == 1

    # Lowercase dept query param
    res_dept = client.get("/v1/analytics/ghost-schedule/2026/2027-1?dept=mis")
    assert res_dept.status_code == 200
    assert len(res_dept.json()) == 1

    # Building filter parameter
    res_bldg = client.get("/v1/analytics/ghost-schedule/2026/2027-1?building=New Hall")
    assert res_bldg.status_code == 200
    assert len(res_bldg.json()) == 1

    res_bldg_none = client.get("/v1/analytics/ghost-schedule/2026/2027-1?building=NonExistent")
    assert res_bldg_none.status_code == 200
    assert len(res_bldg_none.json()) == 0


def test_ghost_schedule_building_fallback_inference(isolated_boundary_env):
    client = isolated_boundary_env["client"]
    db_session = isolated_boundary_env["db"]

    # Room without explicit building column
    room_kb = models.Room(id=20, name="KB 433", building=None, capacity=50)
    course_kb = models.Course(
        id=20,
        term_id="2026/2027-1",
        dept_kisaadi="MIS",
        course_code="MIS 202",
        section="01",
        title="DATA STRUCTURES",
        instructor_id=1,
        credits=3,
        ects=5,
        delivery_method="In-person"
    )
    slot_kb = models.CourseSlot(
        course_id=20,
        day_code="T",
        slot_hour=3,
        slot_title="DATA STRUCTURES",
        room_id=20
    )
    db_session.add_all([room_kb, course_kb, slot_kb])
    db_session.commit()

    res = client.get("/v1/analytics/ghost-schedule/2026/2027-1?dept=MIS")
    assert res.status_code == 200
    items = res.json()
    kb_items = [it for it in items if it["room_name"] == "KB 433"]
    assert len(kb_items) == 1
    # Should infer "Kare Blok" from "KB 433"
    assert kb_items[0]["building"] == "Kare Blok"
    assert kb_items[0]["campus"] == "Kuzey"


def test_ghost_schedule_jf_south_and_ef_north_campus_invariants(isolated_boundary_env):
    client = isolated_boundary_env["client"]
    db_session = isolated_boundary_env["db"]

    # Invariants: JF is in Güney, EF is in Kuzey
    room_jf = models.Room(id=30, name="JF 108", building=None, capacity=40)
    course_jf = models.Course(
        id=30,
        term_id="2026/2027-1",
        dept_kisaadi="PHYS",
        course_code="PHYS 101",
        section="01",
        title="PHYSICS I",
        instructor_id=1,
        credits=4,
        ects=6,
        delivery_method="In-person"
    )
    slot_jf = models.CourseSlot(course_id=30, day_code="W", slot_hour=1, slot_title="PHYSICS", room_id=30)

    room_ef = models.Room(id=31, name="EF 206", building=None, capacity=60)
    course_ef = models.Course(
        id=31,
        term_id="2026/2027-1",
        dept_kisaadi="ED",
        course_code="ED 101",
        section="01",
        title="INTRO TO EDUCATION",
        instructor_id=1,
        credits=3,
        ects=5,
        delivery_method="In-person"
    )
    slot_ef = models.CourseSlot(course_id=31, day_code="W", slot_hour=2, slot_title="EDUCATION", room_id=31)

    db_session.add_all([room_jf, course_jf, slot_jf, room_ef, course_ef, slot_ef])
    db_session.commit()

    res = client.get("/v1/analytics/ghost-schedule/2026/2027-1")
    assert res.status_code == 200
    items = res.json()

    jf_slot = next(it for it in items if it["room_name"] == "JF 108")
    assert jf_slot["building"] == "John Freely Hall"
    assert jf_slot["campus"] == "Güney"

    ef_slot = next(it for it in items if it["room_name"] == "EF 206")
    assert ef_slot["building"] == "Education Faculty"
    assert ef_slot["campus"] == "Kuzey"

    # Test campus filter parameter
    res_guney = client.get("/v1/analytics/ghost-schedule/2026/2027-1?campus=Güney")
    assert res_guney.status_code == 200
    guney_items = res_guney.json()
    assert any(it["room_name"] == "JF 108" for it in guney_items)
    assert not any(it["room_name"] == "EF 206" for it in guney_items)

    res_kuzey = client.get("/v1/analytics/ghost-schedule/2026/2027-1?campus=Kuzey")
    assert res_kuzey.status_code == 200
    kuzey_items = res_kuzey.json()
    assert any(it["room_name"] == "EF 206" for it in kuzey_items)
    assert not any(it["room_name"] == "JF 108" for it in kuzey_items)



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


def test_ghost_schedule_hamlin_hall_south_and_contiguous_slot_expansion(isolated_boundary_env):
    """
    Invariants:
    1. HH (Hamlin Hall) is on Güney Kampüs (not Hisar).
    2. Contiguous slots where room is missing (e.g. 2-hour lab in HH 108) forward-fill the classroom.
    3. 'Campus' is never emitted as a campus name.
    """
    client = isolated_boundary_env["client"]
    db_session = isolated_boundary_env["db"]

    room_hh = models.Room(id=40, name="HH 108 LAB", building=None, capacity=35)
    course_mis = models.Course(
        id=40,
        term_id="2026/2027-1",
        dept_kisaadi="MIS",
        course_code="MIS 131",
        section="01",
        title="INTRO TO ALGORITHMS & PROGRAMMING",
        instructor_id=1,
        credits=4,
        ects=6,
        delivery_method="In-person"
    )
    # Hour 2 has HH 108 LAB, contiguous hour 3 has room_id=None
    slot_hr2 = models.CourseSlot(course_id=40, day_code="F", slot_hour=2, slot_title="LAB", room_id=40)
    slot_hr3 = models.CourseSlot(course_id=40, day_code="F", slot_hour=3, slot_title="LAB", room_id=None)

    db_session.add_all([room_hh, course_mis, slot_hr2, slot_hr3])
    db_session.commit()

    res = client.get("/v1/analytics/ghost-schedule/2026/2027-1?dept=MIS")
    assert res.status_code == 200
    items = res.json()

    # Both hours 2 and 3 must appear with HH 108 LAB
    hh_slots = [it for it in items if it["room_name"] == "HH 108 LAB"]
    assert len(hh_slots) == 2, f"Expected 2 contiguous lab hours, got: {hh_slots}"
    assert {s["slot_hour"] for s in hh_slots} == {2, 3}

    for s in hh_slots:
        assert s["building"] == "Hamlin Hall"
        assert s["campus"] == "Güney"
        assert s["campus"] != "Campus"

