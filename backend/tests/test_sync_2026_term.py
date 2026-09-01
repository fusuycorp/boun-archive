import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Term, Course, Department, Instructor, Room, CourseSlot, SyncState
from scripts.sync_from_scraper import sync_terms_and_new_offerings, backfill_term, ScraperClient, _fetch_upstream_term_runs


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


def _make_course_payloads(term_id, dept, codes):
    return [
        {
            "term": term_id,
            "department": dept,
            "course_code": code,
            "section": "01",
            "course_name": f"{code} TITLE",
            "instructor": "TEST INSTRUCTOR",
            "credits": 3.0,
            "ects": 5.0,
            "delivery_method": "",
            "slots": [],
        }
        for code in codes
    ]


def test_partial_term_reconciliation_backfill():
    """A term already partially ingested locally is re-backfilled when its local
    course count trails the latest completed upstream scrape run."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed the term with a partial snapshot (1 course already ingested).
    session.add(Term(id="2026/2027-1", academic_year="2026/2027", semester_num=1))
    session.add(
        Course(
            term_id="2026/2027-1",
            dept_kisaadi="AD",
            course_code="AD 211",
            section="01",
            title="EARLY SNAPSHOT COURSE",
        )
    )
    session.commit()

    mock_client = MagicMock(spec=ScraperClient)
    full_catalog = _make_course_payloads(
        "2026/2027-1", "AD", ["AD 211", "AD 212", "AD 213", "AD 214", "AD 215"]
    )

    def mock_get(path, params=None):
        if path == "terms":
            return ["2026/2027-1"]
        if path == "feeds/runs":
            return [
                {
                    "term": "2026/2027-1",
                    "status": "completed",
                    "total_courses": 5,
                    "started_at": "2026-08-31T19:26:01+00:00",
                }
            ]
        if "2026-2027-1" in path or (params and params.get("term") == "2026/2027-1"):
            return full_catalog
        return []

    mock_client.get.side_effect = mock_get
    mock_meili = MagicMock()

    synced_count = sync_terms_and_new_offerings(session, mock_client, meili_index=mock_meili)

    # All 5 upstream courses should now be present (1 seeded + 4 new upserts,
    # with the seeded AD 211 refreshed in place rather than duplicated).
    courses = session.query(Course).filter(Course.term_id == "2026/2027-1").all()
    assert len(courses) == 5
    assert synced_count == 5

    ad211 = session.query(Course).filter(Course.course_code == "AD 211").first()
    assert ad211.title == "AD 211 TITLE"


def test_fetch_upstream_term_runs_uses_latest_completed_run():
    """_fetch_upstream_term_runs keeps the newest completed run per term."""
    client = MagicMock(spec=ScraperClient)
    client.get.return_value = [
        {"term": "2026/2027-1", "status": "completed", "total_courses": 90,
         "started_at": "2026-08-30T13:02:42+00:00"},
        {"term": "2026/2027-1", "status": "completed", "total_courses": 3053,
         "started_at": "2026-08-31T18:03:01+00:00"},
        {"term": "2026/2027-1", "status": "completed", "total_courses": 2910,
         "started_at": "2026-08-31T19:26:01+00:00"},
        {"term": "2026/2027-1", "status": "running", "total_courses": 100,
         "started_at": "2026-09-01T00:00:00+00:00"},
        {"term": "2025/2026-3", "status": "completed", "total_courses": 239,
         "started_at": "2026-08-31T18:02:00+00:00"},
    ]
    runs = _fetch_upstream_term_runs(client)
    assert runs["2026/2027-1"] == {"total": 2910, "started_at": "2026-08-31T19:26:01+00:00"}
    assert runs["2025/2026-3"] == {"total": 239, "started_at": "2026-08-31T18:02:00+00:00"}
    # In-flight runs are ignored until they complete.
    assert runs["2026/2027-1"]["total"] != 100


def test_reconciliation_runs_at_most_once_per_upstream_run():
    """A term already reconciled against the latest completed upstream run is
    not re-backfilled on subsequent boots even if its local count permanently
    trails upstream; a newer completed run re-triggers reconciliation."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    session.add(Term(id="2026/2027-1", academic_year="2026/2027", semester_num=1))
    session.add(
        Course(
            term_id="2026/2027-1",
            dept_kisaadi="AD",
            course_code="AD 211",
            section="01",
            title="EARLY SNAPSHOT COURSE",
        )
    )
    session.commit()

    # Upstream claims 5 courses but its export only yields 3: a permanent
    # count mismatch the local DB can never converge.
    full_catalog = _make_course_payloads("2026/2027-1", "AD", ["AD 211", "AD 212", "AD 213"])
    run_started_at = "2026-08-31T19:26:01+00:00"

    def make_mock_get(runs_payload):
        def mock_get(path, params=None):
            if path == "terms":
                return ["2026/2027-1"]
            if path == "feeds/runs":
                return runs_payload
            if "2026-2027-1" in path or (params and params.get("term") == "2026/2027-1"):
                return full_catalog
            return []
        return mock_get

    mock_client = MagicMock(spec=ScraperClient)
    mock_client.get.side_effect = make_mock_get([
        {"term": "2026/2027-1", "status": "completed",
         "total_courses": 5, "started_at": run_started_at},
    ])

    def catalog_fetch_count():
        return sum(
            1
            for c in mock_client.get.call_args_list
            if c.args and (c.args[0] == "courses" or "feeds/exports" in c.args[0])
        )

    # Boot 1: term trails upstream -> reconciliation backfill runs and is recorded.
    synced = sync_terms_and_new_offerings(session, mock_client)
    assert synced == 3
    marker = session.query(SyncState).filter(
        SyncState.feed_name == "term_reconciled:2026/2027-1"
    ).first()
    assert marker is not None
    assert marker.last_cursor == run_started_at
    fetches_after_boot1 = catalog_fetch_count()
    assert fetches_after_boot1 > 0

    # Boot 2: same upstream run -> skip, no catalog re-fetch despite 3 < 5.
    synced = sync_terms_and_new_offerings(session, mock_client)
    assert synced == 0
    assert catalog_fetch_count() == fetches_after_boot1

    # Boot 3: a newer completed run appears -> reconcile again and re-record.
    newer_started_at = "2026-09-01T05:00:00+00:00"
    mock_client.get.side_effect = make_mock_get([
        {"term": "2026/2027-1", "status": "completed",
         "total_courses": 5, "started_at": newer_started_at},
    ])
    synced = sync_terms_and_new_offerings(session, mock_client)
    assert synced == 3
    assert catalog_fetch_count() > fetches_after_boot1
    marker = session.query(SyncState).filter(
        SyncState.feed_name == "term_reconciled:2026/2027-1"
    ).first()
    assert marker.last_cursor == newer_started_at
