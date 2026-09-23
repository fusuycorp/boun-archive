import hmac
import hashlib
import json
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app import models
from app.sync import verify_webhook_signature

@pytest.fixture
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield session
    session.close()
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_db):
    return TestClient(app)


def test_verify_webhook_signature():
    secret = "my_secret_key"
    payload = b'{"event":"test"}'
    valid_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    assert verify_webhook_signature(payload, valid_sig, secret) is True
    assert verify_webhook_signature(payload, f"sha256={valid_sig}", secret) is True
    assert verify_webhook_signature(payload, "invalid_signature", secret) is False
    assert verify_webhook_signature(payload, None, secret) is False
    # If secret is unset, signature validation is skipped
    assert verify_webhook_signature(payload, None, None) is True


def test_webhook_unauthorized_when_secret_set(client, monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "supersecret123")
    payload = json.dumps({"event": "courses.deltas", "deltas": []})

    response = client.post(
        "/v1/webhooks/scraper",
        content=payload,
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid webhook signature"


def test_webhook_deltas_ingestion(client, test_db, monkeypatch):
    secret = "secret_for_test"
    monkeypatch.setenv("WEBHOOK_SECRET", secret)

    delta_payload = {
        "event": "courses.deltas",
        "term": "2026/2027-1",
        "count": 1,
        "timestamp": "2026-09-23T18:00:00Z",
        "deltas": [
            {
                "change_type": "added",
                "term": "2026/2027-1",
                "department": "CMPE",
                "course_code": "CMPE 150",
                "section": "01",
                "timestamp": "2026-09-23T18:00:00Z",
                "new_value": {
                    "course_name": "INTRODUCTION TO COMPUTING",
                    "instructor": "SUZAN USKUDARLI",
                    "credits": 3,
                    "ects": 6,
                    "slots": [
                        {"day": "M", "hour": 3, "room": "BMB 1"},
                        {"day": "M", "hour": 4, "room": ""},
                        {"day": "Th", "hour": 2, "room": "BMB 1"}
                    ]
                }
            }
        ]
    }

    raw_bytes = json.dumps(delta_payload).encode("utf-8")
    sig = hmac.new(secret.encode(), raw_bytes, hashlib.sha256).hexdigest()

    response = client.post(
        "/v1/webhooks/scraper",
        content=raw_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Boun-Signature": sig,
            "X-Boun-Event": "courses.deltas"
        }
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "ok"
    assert res_data["event"] == "courses.deltas"
    assert res_data["received_count"] == 1
    assert res_data["touched_courses"] == 1

    # Verify course exists in PostgreSQL
    course = test_db.query(models.Course).filter(models.Course.course_code == "CMPE 150").first()
    assert course is not None
    assert course.title == "INTRODUCTION TO COMPUTING"
    assert course.instructor.full_name == "SUZAN USKUDARLI"

    # Verify contiguous slots forward-filling
    slots = sorted(course.slots, key=lambda s: (s.day_code, s.slot_hour))
    assert len(slots) == 3
    # Hour 3 on Monday
    assert slots[0].day_code == "M" and slots[0].slot_hour == 3
    assert slots[0].room.name == "BMB 1"
    # Hour 4 on Monday (was blank in payload, forward-filled)
    assert slots[1].day_code == "M" and slots[1].slot_hour == 4
    assert slots[1].room.name == "BMB 1"


def test_webhook_scrape_summary(client, test_db, monkeypatch):
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)

    summary_payload = {
        "event": "scrape.summary",
        "run_id": "run-test-99",
        "term": "2026/2027-1",
        "status": "completed",
        "total_courses": 1500,
        "total_slots": 3200,
        "changes_detected": 12,
        "started_at": "2026-09-23T18:00:00Z",
        "completed_at": "2026-09-23T18:05:00Z"
    }

    response = client.post(
        "/v1/webhooks/scraper",
        json=summary_payload
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["run_id"] == "run-test-99"

    # Verify SyncState was updated
    state = test_db.query(models.SyncState).filter(models.SyncState.feed_name == "upstream_run:run-test-99").first()
    assert state is not None
    assert state.last_cursor == "2026-09-23T18:05:00Z"


def test_system_sync_status(client, test_db):
    # Add sample term and course
    term = models.Term(id="2026/2027-1", academic_year="2026/2027", semester_num=1)
    test_db.add(term)
    dept = models.Department(kisaadi="CMPE", bolum="Computer Engineering")
    test_db.add(dept)
    test_db.commit()

    response = client.get("/v1/system/sync-status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "boun-archive"
    assert data["database"]["total_terms"] == 1
    assert data["database"]["total_departments"] == 1
    assert data["database"]["latest_term"] == "2026/2027-1"
