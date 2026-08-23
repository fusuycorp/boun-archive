import sys
import os
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pathutil import add_import_paths, ROOT_DIR
add_import_paths()

from app.main import app, get_department_unique_courses
from app.analytics import MacroEngine
from app import models

def test_route_registry():
    routes = {getattr(r, "path", None) for r in app.routes if getattr(r, "path", None)}
    
    removed_routes = [
        "/v1/predict/course/{course_code}",
        "/v1/analytics/macro/delivery-evolution",
        "/v1/analytics/macro/course-lifecycles",
        "/v1/analytics/macro/campus-distribution",
        "/v1/analytics/macro/semantic-shift"
    ]
    for r in removed_routes:
        assert r not in routes, f"Deprecated route {r} must not exist in app.routes"

    expected_routes = [
        "/",
        "/health",
        "/v1/search",
        "/v1/facets",
        "/v1/terms",
        "/v1/departments",
        "/v1/departments/{dept_code}/unique-courses",
        "/v1/departments/{dept_code}/instructors",
        "/v1/instructors",
        "/v1/courses/history/{course_code}",
        "/v1/analytics/ghost-schedule/{term:path}",
        "/v1/analytics/macro/departments-evolution",
        "/v1/analytics/macro/scheduling-heatmap"
    ]
    for r in expected_routes:
        assert r in routes, f"Expected route {r} missing from app.routes"
    print("✓ Route registry verification passed.")

async def async_db_tests():
    FastAPICache.init(InMemoryBackend(), prefix="test-cache")

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    models.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Seed test data
        term1 = models.Term(id="2024/2025-1", academic_year="2024/2025", semester_num=1)
        term2 = models.Term(id="2023/2024-1", academic_year="2023/2024", semester_num=1)
        dept = models.Department(kisaadi="CMPE", bolum="Computer Engineering")
        inst = models.Instructor(id=1, full_name="ALICE SMITH")
        room = models.Room(id=1, name="NH 101", building="North")
        c1 = models.Course(id=1, term_id="2024/2025-1", dept_kisaadi="CMPE", course_code="CMPE 150", section="01", title="Intro to Computing", instructor_id=1)
        c2 = models.Course(id=2, term_id="2024/2025-1", dept_kisaadi="CMPE", course_code="CMPE 150", section="02", title="Intro to Computing", instructor_id=1)
        c3 = models.Course(id=3, term_id="2023/2024-1", dept_kisaadi="CMPE", course_code="CMPE 150", section="01", title="Intro to Computing", instructor_id=1)
        s1 = models.CourseSlot(id=1, course_id=1, day_code="M", slot_hour=1, room_id=1)

        db.add_all([term1, term2, dept, inst, room, c1, c2, c3, s1])
        db.commit()

        # Test MacroEngine
        latest_year = MacroEngine.get_latest_data_year(db)
        assert latest_year == 2024, f"Expected 2024, got {latest_year}"

        evo = MacroEngine.get_department_evolution(db)
        assert "departments" in evo and "CMPE" in evo["departments"]

        heatmap = MacroEngine.get_scheduling_heatmap(db)
        assert len(heatmap) == 1
        assert heatmap[0]["day_code"] == "M" and heatmap[0]["slot_hour"] == 1

        # Test unique courses handler
        unique = await get_department_unique_courses("CMPE", db)
        assert len(unique) == 1
        assert unique[0]["course_code"] == "CMPE 150"
        assert len(unique[0]["terms"]) == 2 # 2024/2025-1 and 2023/2024-1
        print("✓ MacroEngine and DB query verification passed.")
    finally:
        db.close()

if __name__ == "__main__":
    test_route_registry()
    asyncio.run(async_db_tests())
    print("All overhaul verification tests passed successfully (Exit 0).")
