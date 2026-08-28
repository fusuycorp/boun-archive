import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

from app.main import app
from app.database import Base, get_db
from app import models

# In-memory SQLite database for test contracts
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    # Initialize in-memory cache for FastAPI Cache
    FastAPICache.init(InMemoryBackend(), prefix="test-cache")
    
    # Create all DB schema tables
    Base.metadata.create_all(bind=engine)
    
    # Seed initial test data
    with TestingSessionLocal() as db:
        term = models.Term(
            id="2024-2025-1",
            academic_year="2024-2025",
            semester_num=1
        )
        dept = models.Department(
            kisaadi="CMPE",
            bolum="Computer Engineering"
        )
        instructor = models.Instructor(
            id=1,
            full_name="Albert Long"
        )
        room = models.Room(
            id=1,
            name="NH101",
            building="New Hall",
            capacity=100
        )
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
        quota = models.QuotaSnapshot(
            id=1,
            term_id="2024-2025-1",
            course_code="CMPE 150",
            section="01",
            department="CMPE",
            status="Open",
            quota="50",
            current="45",
            quota_numeric=50,
            current_numeric=45,
            available=5,
            captured_at="2026-08-28T12:00:00Z"
        )
        change = models.CourseChange(
            id=1,
            change_type="UPDATE",
            term_id="2024-2025-1",
            dept_kisaadi="CMPE",
            course_code="CMPE 150",
            section="01",
            timestamp="2026-08-28T12:00:00Z",
            old_value="TBA",
            new_value="Albert Long",
            details="Instructor updated"
        )
        sync = models.SyncState(
            feed_name="upstream_run",
            last_cursor="2026-08-28T12:00:00Z"
        )

        db.add_all([term, dept, instructor, room, course, slot, quota, change, sync])
        db.commit()

    yield

    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
