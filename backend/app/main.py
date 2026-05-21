import os
import meilisearch
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from redis import asyncio as aioredis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

from . import models, schemas, database

app = FastAPI(title="BOUN Archive API")

# Middlewares
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis = aioredis.from_url(redis_url, encoding="utf8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")

# Meilisearch Client
MEILI_CLIENT = meilisearch.Client(
    os.getenv("MEILI_URL", "http://localhost:7700"), 
    os.getenv("MEILI_MASTER_KEY", "masterKeyLongEnough123")
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the BOUN Archive API"}

@app.get("/api/v1/search")
@cache(expire=600)
def search_courses(
    q: str = "",
    term: List[str] = Query(None),
    dept: List[str] = Query(None),
    instructor: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: str = "asc",
    limit: int = 20,
    offset: int = 0
):
    filter_list = []
    
    if term:
        term_filters = [f"term = '{t}'" for t in term]
        filter_list.append(f"({' OR '.join(term_filters)})")
        
    if dept:
        dept_filters = [f"dept_code = '{d}'" for d in dept]
        filter_list.append(f"({' OR '.join(dept_filters)})")
        
    if instructor:
        filter_list.append(f"instructor = '{instructor}'")

    sort_list = []
    if sort_by:
        sort_list.append(f"{sort_by}:{sort_order}")
    else:
        # Default sort
        sort_list = ['term:desc', 'course_code:asc']

    results = MEILI_CLIENT.index('courses').search(q, {
        'filter': " AND ".join(filter_list) if filter_list else None,
        'limit': limit,
        'offset': offset,
        'facets': ['term', 'dept_code', 'instructor', 'delivery_method'],
        'sort': sort_list
    })
    return results

@app.get("/api/v1/facets")
@cache(expire=3600)
def get_global_facets():
    # Return facets for all documents (empty search)
    results = MEILI_CLIENT.index('courses').search("", {
        'facets': ['term', 'dept_code', 'delivery_method'],
        'limit': 0
    })
    return results['facetDistribution']

@app.get("/api/v1/analytics/ghost-schedule/{term:path}")
@cache(expire=3600)
def get_ghost_schedule(
    term: str, 
    dept: List[str] = Query(None),
    db: Session = Depends(database.get_db)
):
    # Reconstruct campus layout for a term
    query = db.query(
        models.CourseSlot.day_code,
        models.CourseSlot.slot_hour,
        models.Room.name.label("room_name"),
        models.Course.course_code,
        models.Course.dept_kisaadi
    ).join(models.Course).join(models.Room).filter(models.Course.term_id == term)
    
    if dept:
        query = query.filter(models.Course.dept_kisaadi.in_(dept))
        
    results = query.all()
    
    # Convert Row objects to dictionaries for JSON serialization
    return [r._asdict() for r in results]

from .analytics import TrendEngine

# Load analytics engine (in a real app, do this once or use a dependency)
def get_engine(db: Session = Depends(database.get_db)):
    # This is heavy for every request, but for demo/small data it's okay.
    # Ideally, pre-calculate or use a subset.
    courses_df = pd.read_sql(db.query(models.Course).statement, db.bind)
    slots_df = pd.read_sql(db.query(models.CourseSlot).statement, db.bind)
    return TrendEngine(courses_df, slots_df)

@app.get("/api/v1/predict/course/{course_code}")
@cache(expire=3600)
def predict_course(course_code: str, db: Session = Depends(database.get_db)):
    # For performance in this demo, we'll query only the relevant history
    history = db.query(models.Course).filter(models.Course.course_code == course_code).all()
    if not history:
        raise HTTPException(status_code=404, detail="Course not found")
    
    course_ids = [c.id for c in history]
    slots = db.query(models.CourseSlot, models.Course.term_id).join(models.Course).filter(models.CourseSlot.course_id.in_(course_ids)).all()
    
    # Convert to DF for the existing engine logic
    c_df = pd.DataFrame([{
        'id': c.id, 
        'course_code': c.course_code, 
        'term': c.term_id
    } for c in history])
    
    s_df = pd.DataFrame([{
        'course_id': s.CourseSlot.course_id,
        'day': s.CourseSlot.day_code,
        'hour': s.CourseSlot.slot_hour,
        'term': s.term_id
    } for s in slots])
    
    engine = TrendEngine(c_df, s_df)
    return {
        "course_code": course_code,
        "offering_probability": engine.predict_offering(course_code),
        "predicted_slots": engine.predict_slots(course_code)
    }

@app.get("/api/v1/courses/{course_id}", response_model=schemas.Course)
@cache(expire=3600)
def get_course(course_id: int, db: Session = Depends(database.get_db)):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@app.get("/api/v1/instructors", response_model=List[schemas.Instructor])
@cache(expire=3600)
def get_instructors(q: str = "", db: Session = Depends(database.get_db)):
    query = db.query(models.Instructor)
    if q:
        query = query.filter(models.Instructor.full_name.ilike(f"%{q}%"))
    return query.limit(50).all()

@app.get("/api/v1/analytics/instructor/{instructor_id}/legacy")
@cache(expire=3600)
def get_instructor_legacy(instructor_id: int, db: Session = Depends(database.get_db)):
    instructor = db.query(models.Instructor).filter(models.Instructor.id == instructor_id).first()
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor not found")
    
    courses = db.query(models.Course).filter(models.Course.instructor_id == instructor_id).all()
    
    # Calculate legacy metrics
    total_semesters = len(set([c.term_id for c in courses]))
    most_frequent = pd.Series([c.course_code for c in courses]).value_counts().head(5).to_dict()
    
    # Preferred slots (joining with course_slots)
    course_ids = [c.id for c in courses]
    slots = db.query(
        models.CourseSlot.day_code,
        models.CourseSlot.slot_hour
    ).filter(models.CourseSlot.course_id.in_(course_ids)).all()
    
    preferred_slots = pd.DataFrame([{'day': s.day_code, 'hour': s.slot_hour} for s in slots])
    if not preferred_slots.empty:
        slots_count = preferred_slots.groupby(['day', 'hour']).size().reset_index(name='frequency')
        slots_count = slots_count.sort_values(by='frequency', ascending=False).head(5).to_dict(orient='records')
    else:
        slots_count = []

    return {
        "instructor_name": instructor.full_name,
        "total_semesters_taught": total_semesters,
        "total_courses_taught": len(courses),
        "most_frequent_courses": most_frequent,
        "preferred_slots": slots_count,
        "history": sorted([{
            "term": c.term_id,
            "course_code": c.course_code,
            "title": c.title
        } for c in courses], key=lambda x: x['term'], reverse=True)
    }

@app.get("/api/v1/terms", response_model=List[schemas.Term])
@cache(expire=86400)
def get_terms(db: Session = Depends(database.get_db)):
    return db.query(models.Term).order_by(models.Term.id.desc()).all()

@app.get("/api/v1/departments", response_model=List[schemas.Department])
@cache(expire=86400)
def get_departments(db: Session = Depends(database.get_db)):
    return db.query(models.Department).order_by(models.Department.kisaadi).all()

@app.get("/api/v1/departments/{dept_code}/unique-courses")
@cache(expire=3600)
def get_department_unique_courses(dept_code: str, db: Session = Depends(database.get_db)):
    # Get all unique courses for this department and the terms they were offered in
    courses = db.query(
        models.Course.course_code,
        models.Course.title,
        models.Course.term_id
    ).filter(models.Course.dept_kisaadi == dept_code).all()
    
    unique_courses = {}
    for c in courses:
        if c.course_code not in unique_courses:
            unique_courses[c.course_code] = {
                "course_code": c.course_code,
                "title": c.title,
                "terms": set()
            }
        unique_courses[c.course_code]["terms"].add(c.term_id)
        
    # Convert sets to sorted lists for JSON
    result = []
    for code in sorted(unique_courses.keys()):
        course_data = unique_courses[code]
        course_data["terms"] = sorted(list(course_data["terms"]), reverse=True)
        result.append(course_data)
        
    return result

@app.get("/api/v1/courses/history/{course_code}")
@cache(expire=3600)
def get_course_history(course_code: str, db: Session = Depends(database.get_db)):
    # Get all instances of this course code across all terms
    courses = db.query(models.Course).filter(models.Course.course_code == course_code).all()
    if not courses:
        raise HTTPException(status_code=404, detail="Course history not found")
        
    result = []
    for c in courses:
        slots = db.query(models.CourseSlot).filter(models.CourseSlot.course_id == c.id).all()
        result.append({
            "id": c.id,
            "term_id": c.term_id,
            "section": c.section,
            "title": c.title,
            "instructor": c.instructor.full_name if c.instructor else "TBA",
            "credits": c.credits,
            "ects": c.ects,
            "delivery_method": c.delivery_method,
            "slots": [{
                "day": s.day_code,
                "hour": s.slot_hour,
                "room": s.room.name if s.room else "N/A",
                "title": s.slot_title
            } for s in slots]
        })
        
    # Sort by term (desc) and section (asc)
    return sorted(result, key=lambda x: (x['term_id'], x['section']), reverse=True)
