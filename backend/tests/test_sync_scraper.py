import os
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.models import Base, Term, Course, Department, Instructor, Room, CourseSlot
from scripts.sync_from_scraper import (
    ensure_term,
    _upsert_course,
    sync_terms_and_new_offerings,
    _fetch_term_courses
)

@pytest.fixture
def sync_db():
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    yield session
    session.close()

def test_ensure_term_2026_2027(sync_db):
    term = ensure_term(sync_db, "2026/2027-1")
    assert term is not None
    assert term.id == "2026/2027-1"
    assert term.academic_year == "2026/2027"
    assert term.semester_num == 1

def test_sync_terms_and_new_offerings_discovers_new_term(sync_db):
    client = MagicMock()
    def mock_get(path, params=None):
        if path == "terms":
            return ["2026/2027-1", "2025/2026-3"]
        if path == "courses" and params and params.get("term") == "2026/2027-1":
            return {"items": [{
                "id": 101,
                "term": "2026/2027-1",
                "department": "HIST",
                "course_code": "HIST 49S",
                "section": "01",
                "course_name": "HISTORICAL TOPICS",
                "instructor": "Edhem Eldem",
                "credits": 3,
                "ects": 6,
                "delivery_method": "Face-to-Face",
                "slots": [{"day": "M", "hour": 7, "room": "NH101"}]
            }], "total": 1}
        if path == "courses":
            return {"items": [], "total": 0}
        return None

    client.get.side_effect = mock_get

    synced = sync_terms_and_new_offerings(sync_db, client, meili_index=None, dry_run=False)
    assert synced == 1

    terms = sync_db.query(Term).all()
    term_ids = [t.id for t in terms]
    assert "2026/2027-1" in term_ids
    assert "2025/2026-3" in term_ids

    course = sync_db.query(Course).filter(Course.term_id == "2026/2027-1").first()
    assert course is not None
    assert course.course_code == "HIST 49S"
    assert course.title == "HISTORICAL TOPICS"
    assert len(course.slots) == 1
    assert course.slots[0].day_code == "M"
    assert course.slots[0].slot_hour == 7

def test_fetch_term_courses_fallback():
    client = MagicMock()
    # Simulate export endpoint failing with 502/404, fallback to paginated /courses
    def mock_get(path, params=None):
        if path.startswith("feeds/exports"):
            raise Exception("502 Bad Gateway")
        if path == "courses":
            return {
                "items": [{"id": 1, "course_code": "HIST 49S", "section": "01"}],
                "total": 1
            }
        return None

    client.get.side_effect = mock_get
    courses = _fetch_term_courses(client, "2026/2027-1")
    assert len(courses) == 1
    assert courses[0]["course_code"] == "HIST 49S"
