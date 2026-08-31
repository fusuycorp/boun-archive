import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Term, Course, Department, Instructor, Room, CourseSlot
from scripts.sync_from_scraper import sync_terms_and_new_offerings, backfill_term, ScraperClient


def test_sync_2026_term_ingestion():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    mock_client = MagicMock(spec=ScraperClient)
    # Mock scraper terms
    def mock_get(path, params=None):
        if path == "terms":
            return ["2026/2027-1", "2025/2026-3"]
        if "2026-2027-1" in path or "2026%2F2027-1" in path or (params and params.get("term") == "2026/2027-1"):
            return [
                {
                    "term": "2026/2027-1",
                    "department": "AD",
                    "course_code": "AD  211",
                    "section": "01",
                    "course_name": "FINANCIAL ACCOUNTING FOR ECONOMISTS",
                    "instructor": "FATİH F.YILMAZ",
                    "credits": 3.0,
                    "ects": 4.0,
                    "delivery_method": "Standard",
                    "slots": [
                        {
                            "day": "M",
                            "hour": "3",
                            "room": "M 1171",
                            "slot_title": "FINANCIAL ACCOUNTING FOR ECONOMISTS",
                            "instructor": "FATİH F.YILMAZ"
                        },
                        {
                            "day": "M",
                            "hour": "4",
                            "room": "M 1171",
                            "slot_title": "FINANCIAL ACCOUNTING FOR ECONOMISTS",
                            "instructor": "FATİH F.YILMAZ"
                        }
                    ]
                },
                {
                    "term": "2026/2027-1",
                    "department": "CMPE",
                    "course_code": "CMPE 150",
                    "section": "01",
                    "course_name": "INTRODUCTION TO COMPUTING",
                    "instructor": "SUZAN ÜSKÜDARLI",
                    "credits": 3.0,
                    "ects": 6.0,
                    "delivery_method": "Standard",
                    "slots": [
                        {
                            "day": "Th",
                            "hour": "5",
                            "room": "NH 101",
                            "slot_title": "INTRODUCTION TO COMPUTING",
                            "instructor": "SUZAN ÜSKÜDARLI"
                        }
                    ]
                }
            ]
        return []

    mock_client.get.side_effect = mock_get

    mock_meili = MagicMock()

    synced_count = sync_terms_and_new_offerings(session, mock_client, meili_index=mock_meili)
    assert synced_count == 2

    # Verify Term was inserted
    term = session.query(Term).filter(Term.id == "2026/2027-1").first()
    assert term is not None
    assert term.academic_year == "2026/2027"
    assert term.semester_num == 1

    # Verify Courses were inserted
    courses = session.query(Course).filter(Course.term_id == "2026/2027-1").all()
    assert len(courses) == 2

    ad211 = session.query(Course).filter(Course.course_code == "AD 211").first()
    assert ad211 is not None
    assert ad211.title == "FINANCIAL ACCOUNTING FOR ECONOMISTS"
    assert ad211.instructor.full_name == "FATİH F.YILMAZ"
    assert len(ad211.slots) == 2
    assert ad211.slots[0].day_code == "M"
    assert ad211.slots[0].slot_hour == 3
    assert ad211.slots[0].room.name == "M 1171"

    # Verify Meilisearch sync was invoked
    assert mock_meili.add_documents.called
    docs = mock_meili.add_documents.call_args[0][0]
    assert len(docs) == 2
    assert docs[0]["term"] == "2026/2027-1"
    assert docs[0]["course_code"] == "AD 211"
