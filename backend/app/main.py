import os
import hashlib
import logging
import meilisearch
from meilisearch.errors import MeilisearchApiError
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from typing import Literal, List, Optional
from redis import asyncio as aioredis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

from . import models, schemas, database
from .analytics import MacroEngine

ALLOWED_SORTS = {"term", "course_code", "title", "instructor", "credits", "ects"}

logger = logging.getLogger(__name__)

def escape_meili_filter(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")

def escape_sql_wildcards(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

def custom_key_builder(
    func,
    namespace: str = "",
    *,
    request = None,
    response = None,
    args,
    kwargs,
) -> str:
    # Filter out Session/db objects to prevent unique DB connection representation causing cache misses
    filtered_args = tuple(arg for arg in args if not isinstance(arg, Session))
    filtered_kwargs = {
        k: v for k, v in kwargs.items()
        if not isinstance(v, Session) and k != "db"
    }
    cache_key = hashlib.md5(
        f"{func.__module__}:{func.__name__}:{filtered_args}:{filtered_kwargs}".encode()
    ).hexdigest()
    return f"{namespace}:{cache_key}"

@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis = aioredis.from_url(redis_url)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache", key_builder=custom_key_builder)
    
    # Ensure Meilisearch 'courses' index exists with primary key 'id'
    try:
        MEILI_CLIENT.create_index('courses', {'primaryKey': 'id'})
    except MeilisearchApiError as e:
        if e.code != "index_already_exists":
            logger.error("Failed to create Meilisearch 'courses' index: %s", e)

    try:
        yield
    finally:
        if hasattr(redis, "aclose"):
            await redis.aclose()
        elif hasattr(redis, "close"):
            await redis.close()

app = FastAPI(title="BOUN Archive API", lifespan=lifespan)

# Middlewares
app.add_middleware(GZipMiddleware, minimum_size=1000)

cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Meilisearch Client
MEILI_MASTER_KEY = os.getenv("MEILI_MASTER_KEY")
if not MEILI_MASTER_KEY:
    raise RuntimeError("MEILI_MASTER_KEY must be set")

MEILI_CLIENT = meilisearch.Client(
    os.getenv("MEILI_URL", "http://localhost:7700"), 
    MEILI_MASTER_KEY
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the BOUN Archive API"}

@app.get("/health")
@app.head("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/v1/system/status", response_model=schemas.SystemStatusResponse)
@app.get("/v1/sync/status", response_model=schemas.SystemStatusResponse)
@cache(expire=30)
def get_system_status(db: Session = Depends(database.get_db)):
    sync_states = db.query(models.SyncState).all()
    feed_map = {}
    latest_ts = None

    for s in sync_states:
        feed_map[s.feed_name] = {
            "last_cursor": s.last_cursor,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None
        }
        if s.last_cursor:
            if latest_ts is None or s.last_cursor > latest_ts:
                latest_ts = s.last_cursor
        elif s.updated_at:
            iso_u = s.updated_at.isoformat()
            if latest_ts is None or iso_u > latest_ts:
                latest_ts = iso_u

    if not latest_ts:
        latest_change = db.query(func.max(models.CourseChange.timestamp)).scalar()
        latest_quota = db.query(func.max(models.QuotaSnapshot.captured_at)).scalar()
        candidates = [c for c in [latest_change, latest_quota] if c]
        if candidates:
            latest_ts = max(candidates)

    return {
        "status": "healthy",
        "latest_scrape_time": latest_ts,
        "feeds": feed_map
    }

@app.get("/v1/search")
@cache(expire=600)
def search_courses(
    q: str = "",
    term: List[str] = Query(None),
    dept: List[str] = Query(None),
    instructor: Optional[str] = None,
    sort_by: Optional[str] = Query(None),
    sort_order: Literal["asc", "desc"] = "asc",
    limit: int = Query(20, ge=0, le=100),
    offset: int = Query(0, ge=0, le=10_000)
):
    filter_list = []
    
    if term:
        term_filters = []
        for t in term:
            escaped = escape_meili_filter(t)
            term_filters.append(f"term = '{escaped}'")
        filter_list.append(f"({' OR '.join(term_filters)})")
        
    if dept:
        dept_filters = []
        for d in dept:
            escaped = escape_meili_filter(d)
            dept_filters.append(f"dept_code = '{escaped}'")
        filter_list.append(f"({' OR '.join(dept_filters)})")
        
    if instructor:
        escaped_instructor = escape_meili_filter(instructor)
        filter_list.append(f"instructor = '{escaped_instructor}'")

    sort_list = []
    if sort_by:
        if sort_by not in ALLOWED_SORTS:
            raise HTTPException(status_code=422, detail=f"sort_by must be one of {sorted(ALLOWED_SORTS)}")
        sort_list.append(f"{sort_by}:{sort_order}")
    else:
        # Default sort
        sort_list = ['term:desc', 'course_code:asc']

    try:
        results = MEILI_CLIENT.index('courses').search(q, {
            'filter': " AND ".join(filter_list) if filter_list else None,
            'limit': limit,
            'offset': offset,
            'facets': ['term', 'dept_code', 'instructor', 'delivery_method'],
            'sort': sort_list
        })
        return results
    except MeilisearchApiError as e:
        if e.code == "index_not_found":
            raise HTTPException(status_code=503, detail="Search index not ready")
        raise HTTPException(status_code=500, detail="Search service error")

@app.get("/v1/facets")
@cache(expire=3600)
def get_global_facets():
    try:
        # Return facets for all documents (empty search)
        results = MEILI_CLIENT.index('courses').search("", {
            'facets': ['term', 'dept_code', 'delivery_method'],
            'limit': 0
        })
        return results.get('facetDistribution', {})
    except MeilisearchApiError as e:
        if e.code == "index_not_found":
            raise HTTPException(status_code=503, detail="Search index not ready")
        raise HTTPException(status_code=500, detail="Search service error")

@app.get("/v1/analytics/ghost-schedule/{term:path}")
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

# Macro Analytics Endpoints
@app.get("/v1/analytics/macro/departments-evolution")
@cache(expire=86400)
def get_dept_evolution(db: Session = Depends(database.get_db)):
    return MacroEngine.get_department_evolution(db)

@app.get("/v1/analytics/macro/scheduling-heatmap")
@cache(expire=86400)
def get_heatmap(decade: Optional[int] = Query(None), db: Session = Depends(database.get_db)):
    return MacroEngine.get_scheduling_heatmap(db, decade)

@app.get("/v1/courses/{course_id}", response_model=schemas.Course)
@cache(expire=3600)
def get_course(course_id: int, db: Session = Depends(database.get_db)):
    course = db.query(models.Course).options(
        joinedload(models.Course.slots).joinedload(models.CourseSlot.room)
    ).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@app.get("/v1/instructors", response_model=List[schemas.Instructor])
@cache(expire=3600)
def get_instructors(q: str = "", db: Session = Depends(database.get_db)):
    query = db.query(models.Instructor)
    if q:
        clean_q = escape_sql_wildcards(q.strip())
        query = query.filter(models.Instructor.full_name.ilike(f"%{clean_q}%"))
    return query.limit(50).all()

@app.get("/v1/instructors/{instructor_id}", response_model=schemas.Instructor)
@cache(expire=3600)
def get_instructor(instructor_id: int, db: Session = Depends(database.get_db)):
    instructor = db.query(models.Instructor).filter(models.Instructor.id == instructor_id).first()
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor not found")
    return instructor

@app.get("/v1/analytics/instructor/{instructor_id}/legacy")
@cache(expire=3600)
def get_instructor_legacy(instructor_id: int, db: Session = Depends(database.get_db)):
    instructor = db.query(models.Instructor).filter(models.Instructor.id == instructor_id).first()
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor not found")
    
    # Calculate legacy metrics using SQL GROUP BY
    most_frequent_query = db.query(
        models.Course.course_code,
        func.count(models.Course.id).label("freq")
    ).filter(
        models.Course.instructor_id == instructor_id
    ).group_by(
        models.Course.course_code
    ).order_by(
        func.count(models.Course.id).desc()
    ).limit(5).all()
    most_frequent = {row.course_code: row.freq for row in most_frequent_query}

    preferred_slots_query = db.query(
        models.CourseSlot.day_code,
        models.CourseSlot.slot_hour,
        func.count(models.CourseSlot.id).label("freq")
    ).join(
        models.Course
    ).filter(
        models.Course.instructor_id == instructor_id,
        models.CourseSlot.day_code.isnot(None),
        models.CourseSlot.slot_hour.isnot(None)
    ).group_by(
        models.CourseSlot.day_code,
        models.CourseSlot.slot_hour
    ).order_by(
        func.count(models.CourseSlot.id).desc()
    ).limit(5).all()

    slots_count = [
        {"day": row.day_code, "hour": int(row.slot_hour), "frequency": row.freq}
        for row in preferred_slots_query
    ]

    courses = db.query(models.Course).filter(models.Course.instructor_id == instructor_id).all()
    total_semesters = len(set([c.term_id for c in courses]))

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

@app.get("/v1/terms", response_model=List[schemas.Term])
@cache(expire=86400)
def get_terms(db: Session = Depends(database.get_db)):
    terms = db.query(models.Term).order_by(models.Term.id.desc()).all()
    return [schemas.Term.model_validate(t).model_dump() for t in terms]

@app.get("/v1/departments", response_model=List[schemas.Department])
@cache(expire=86400)
def get_departments(db: Session = Depends(database.get_db)):
    depts = db.query(models.Department).order_by(models.Department.kisaadi).all()
    return [schemas.Department.model_validate(d).model_dump() for d in depts]

@app.get("/v1/departments/{dept_code}/unique-courses")
@cache(expire=3600)
def get_department_unique_courses(dept_code: str, db: Session = Depends(database.get_db)):
    # Query distinct course_code, title, term_id to minimize row transfer and in-memory deduplication
    courses = db.query(
        models.Course.course_code,
        models.Course.title,
        models.Course.term_id
    ).filter(
        models.Course.dept_kisaadi == dept_code
    ).distinct().order_by(
        models.Course.course_code,
        models.Course.term_id.desc()
    ).all()
    
    unique_courses = {}
    for code, title, term_id in courses:
        if code not in unique_courses:
            unique_courses[code] = {
                "course_code": code,
                "title": title or "",
                "terms": []
            }
        unique_courses[code]["terms"].append(term_id)
        
    return [unique_courses[code] for code in sorted(unique_courses.keys())]

@app.get("/v1/departments/{dept_code}/instructors")
@cache(expire=3600)
def get_department_instructors(dept_code: str, db: Session = Depends(database.get_db)):
    results = db.query(
        models.Instructor.id,
        models.Instructor.full_name,
        func.max(models.Course.term_id).label("last_term"),
        func.count(models.Course.id).label("course_count"),
        func.count(func.distinct(models.Course.term_id)).label("total_semesters")
    ).join(models.Course).filter(models.Course.dept_kisaadi == dept_code).group_by(
        models.Instructor.id, models.Instructor.full_name
    ).order_by(func.max(models.Course.term_id).desc()).all()
    
    return [
        {
            "id": r.id,
            "full_name": r.full_name,
            "last_term": r.last_term,
            "course_count": r.course_count,
            "total_semesters": r.total_semesters
        }
        for r in results
    ]

@app.get("/v1/courses/history/{course_code}")
@cache(expire=3600)
def get_course_history(course_code: str, db: Session = Depends(database.get_db)):
    clean_code = " ".join(course_code.strip().split())
    if not clean_code:
        raise HTTPException(status_code=404, detail="Course history not found")
    
    courses = db.query(models.Course).options(
        joinedload(models.Course.instructor),
        joinedload(models.Course.slots).joinedload(models.CourseSlot.room)
    ).filter(
        func.upper(models.Course.course_code) == clean_code.upper()
    ).limit(300).all()
    
    if not courses:
        no_spaces = clean_code.replace(" ", "").upper()
        courses = db.query(models.Course).options(
            joinedload(models.Course.instructor),
            joinedload(models.Course.slots).joinedload(models.CourseSlot.room)
        ).filter(
            func.upper(func.replace(models.Course.course_code, ' ', '')) == no_spaces
        ).limit(300).all()
        
    if not courses:
        raise HTTPException(status_code=404, detail="Course history not found")
        
    result = []
    for c in courses:
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
            } for s in c.slots]
        })
        
    result.sort(key=lambda x: x['section'] or '')
    result.sort(key=lambda x: x['term_id'], reverse=True)
    return result

@app.get("/v1/courses/{course_code}/quota", response_model=List[schemas.QuotaSnapshot])
@cache(expire=60)
def get_course_quota(
    course_code: str,
    term: Optional[str] = Query(None),
    history: bool = Query(False),
    db: Session = Depends(database.get_db)
):
    clean_code = " ".join(course_code.strip().split())
    if not clean_code:
        return []

    target_term = term
    if not target_term:
        latest_term = db.query(models.QuotaSnapshot.term_id).filter(
            func.upper(models.QuotaSnapshot.course_code) == clean_code.upper()
        ).order_by(models.QuotaSnapshot.term_id.desc()).first()
        if latest_term:
            target_term = latest_term[0]

    query = db.query(models.QuotaSnapshot).filter(
        func.upper(models.QuotaSnapshot.course_code) == clean_code.upper()
    )
    if target_term:
        query = query.filter(models.QuotaSnapshot.term_id == target_term)

    if history:
        snapshots = query.order_by(
            models.QuotaSnapshot.captured_at.desc()
        ).limit(200).all()
        return snapshots

    try:
        snapshots = query.distinct(
            models.QuotaSnapshot.section,
            models.QuotaSnapshot.department
        ).order_by(
            models.QuotaSnapshot.section,
            models.QuotaSnapshot.department,
            models.QuotaSnapshot.captured_at.desc()
        ).all()
    except Exception:
        all_snaps = query.order_by(models.QuotaSnapshot.captured_at.desc()).limit(1000).all()
        seen = set()
        snapshots = []
        for s in all_snaps:
            k = (s.section, s.department)
            if k not in seen:
                seen.add(k)
                snapshots.append(s)

    snapshots.sort(key=lambda x: (x.section or '', x.department or ''))
    return [schemas.QuotaSnapshot.model_validate(s).model_dump() for s in snapshots]

@app.get("/v1/courses/{course_code}/changes", response_model=List[schemas.CourseChange])
@cache(expire=60)
def get_course_changes(
    course_code: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(database.get_db)
):
    clean_code = " ".join(course_code.strip().split())
    if not clean_code:
        return []

    changes = db.query(models.CourseChange).filter(
        func.upper(models.CourseChange.course_code) == clean_code.upper()
    ).order_by(
        models.CourseChange.timestamp.desc()
    ).limit(limit).all()

    return [schemas.CourseChange.model_validate(c).model_dump() for c in changes]

