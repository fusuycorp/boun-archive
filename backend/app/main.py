import os
import hashlib
import logging
import meilisearch
from meilisearch.errors import MeilisearchApiError
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload, selectinload
from datetime import datetime, timezone
from typing import Literal, List, Optional
from redis import asyncio as aioredis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

from . import models, schemas, database
from .analytics import MacroEngine
from .semantic import (
    course_history_to_json_ld,
    instructor_to_json_ld,
    departments_to_json_ld,
    generate_course_schedule_ics
)

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
    # Filter out Session/db/Request objects to prevent unique DB connection representation causing cache misses
    filtered_args = tuple(arg for arg in args if not isinstance(arg, (Session, Request)))
    filtered_kwargs = {
        k: v for k, v in kwargs.items()
        if not isinstance(v, (Session, Request)) and k not in ("db", "request")
    }
    accept_hdr = request.headers.get("accept", "") if request and hasattr(request, "headers") else ""
    cache_key = hashlib.md5(
        f"{func.__module__}:{func.__name__}:{filtered_args}:{filtered_kwargs}:{accept_hdr}".encode()
    ).hexdigest()
    return f"{namespace}:{cache_key}"

@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis = aioredis.from_url(redis_url)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache", key_builder=custom_key_builder)
    
    # Ensure Meilisearch 'courses' index exists with primary key 'id' and correct settings
    try:
        try:
            MEILI_CLIENT.create_index('courses', {'primaryKey': 'id'})
        except MeilisearchApiError as e:
            if e.code != "index_already_exists":
                logger.error("Failed to create Meilisearch 'courses' index: %s", e)

        MEILI_CLIENT.index('courses').update_settings({
            'filterableAttributes': [
                'term', 'dept_code', 'department', 'instructor', 'instructor_id', 'delivery_method'
            ],
            'searchableAttributes': [
                'course_code', 'title', 'instructor', 'department'
            ],
            'faceting': {
                'maxValuesPerFacet': 10000
            },
            'pagination': {
                'maxTotalHits': 200000
            },
            'sortableAttributes': ['term', 'course_code', 'title', 'instructor', 'credits', 'ects']
        })

        # Check if Meilisearch 'courses' index has documents; if 0, auto-sync in background
        try:
            stats = MEILI_CLIENT.index('courses').get_stats()
            doc_count = getattr(stats, 'number_of_documents', None)
            if doc_count is None and isinstance(stats, dict):
                doc_count = stats.get('numberOfDocuments', 0)
            if doc_count == 0:
                logger.info("Meilisearch 'courses' index has 0 documents. Triggering background sync from PostgreSQL...")
                import threading
                import sys
                from pathlib import Path
                root_path = str(Path(__file__).resolve().parent.parent)
                if root_path not in sys.path:
                    sys.path.insert(0, root_path)
                try:
                    from scripts.sync_meilisearch import sync_meilisearch
                    threading.Thread(target=sync_meilisearch, kwargs={"force": True}, daemon=True).start()
                except Exception as sync_err:
                    logger.warning("Could not import or start sync_meilisearch: %s", sync_err)
        except Exception as e:
            logger.warning("Meilisearch stats check failed on startup: %s", e)
    except Exception as e:
        logger.warning("Meilisearch setup/configuration encountered an issue on startup: %s", e)

    # 3. Start background scraper sync on boot to discover new terms immediately
    import threading
    threading.Thread(target=_run_scraper_sync_job, kwargs={"mode": "incremental"}, daemon=True).start()

    try:
        yield
    finally:
        if hasattr(redis, "aclose"):
            await redis.aclose()
        elif hasattr(redis, "close"):
            await redis.close()

def _run_scraper_sync_job(term_id: Optional[str] = None, mode: str = "incremental") -> None:
    """Helper executed in background thread to sync from scraper and update DB + Meilisearch."""
    import subprocess
    import sys
    from pathlib import Path
    
    app_dir = Path(__file__).resolve().parent.parent
    candidates = [
        app_dir / "scripts" / "sync_from_scraper.py",
        app_dir.parent / "scripts" / "sync_from_scraper.py",
        Path("/app/scripts/sync_from_scraper.py")
    ]
    script_path = next((str(p) for p in candidates if p.exists()), None)
    if not script_path:
        logger.warning("Could not locate scripts/sync_from_scraper.py in candidate paths.")
        return

    working_dir = str(Path(script_path).parent.parent)
    cmd = [sys.executable, script_path, "--mode", mode]
    if term_id:
        cmd.extend(["--term", term_id])
    try:
        logger.info("Executing background scraper sync: %s", " ".join(cmd))
        proc = subprocess.run(cmd, cwd=working_dir, capture_output=True, text=True, timeout=600)
        if proc.returncode == 0:
            logger.info("Background scraper sync completed successfully.")
        else:
            logger.warning("Background scraper sync finished with code %d: %s", proc.returncode, proc.stderr[:300])
    except Exception as e:
        logger.error("Background scraper sync execution failed: %s", e)

app = FastAPI(
    title="BOUN Archive API",
    description="Open Data & Semantic Linked Data API for Boğaziçi University's academic catalog, course history, schedules, and quota analytics.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Middlewares
app.add_middleware(GZipMiddleware, minimum_size=1000)

cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)

# Meilisearch Client
MEILI_MASTER_KEY = os.getenv("MEILI_MASTER_KEY") or "boun_meili_master_key"

MEILI_CLIENT = meilisearch.Client(
    os.getenv("MEILI_URL", "http://localhost:7700"), 
    MEILI_MASTER_KEY
)

def _get_global_facets_from_db(db: Session) -> dict:
    try:
        term_counts = dict(
            db.query(models.Course.term_id, func.count(models.Course.id))
            .group_by(models.Course.term_id)
            .all()
        )
        dept_counts = dict(
            db.query(models.Course.dept_kisaadi, func.count(models.Course.id))
            .group_by(models.Course.dept_kisaadi)
            .all()
        )
        delivery_counts = dict(
            db.query(models.Course.delivery_method, func.count(models.Course.id))
            .filter(models.Course.delivery_method.isnot(None))
            .group_by(models.Course.delivery_method)
            .all()
        )
        return {
            "term": term_counts,
            "dept_code": dept_counts,
            "delivery_method": delivery_counts
        }
    except Exception as e:
        logger.error("DB facet fallback error: %s", e)
        return {"term": {}, "dept_code": {}, "delivery_method": {}}

def _search_courses_from_db(
    db: Session,
    q: str,
    term: Optional[List[str]],
    dept: Optional[List[str]],
    instructor: Optional[str],
    sort_by: Optional[str],
    sort_order: str,
    limit: int,
    offset: int
) -> dict:
    try:
        query = db.query(models.Course).options(
            joinedload(models.Course.department),
            joinedload(models.Course.instructor),
            selectinload(models.Course.slots).joinedload(models.CourseSlot.room)
        )
        
        has_instructor_join = False
        has_dept_join = False
        
        if q and q.strip():
            clean_q = escape_sql_wildcards(q.strip())
            clean_q_nospace = clean_q.replace(" ", "")
            pattern = f"%{clean_q}%"
            pattern_nospace = f"%{clean_q_nospace}%"
            
            query = query.outerjoin(models.Instructor).outerjoin(models.Department)
            has_instructor_join = True
            has_dept_join = True
            
            query = query.filter(
                or_(
                    models.Course.course_code.ilike(pattern),
                    func.replace(models.Course.course_code, ' ', '').ilike(pattern_nospace),
                    models.Course.title.ilike(pattern),
                    models.Course.dept_kisaadi.ilike(pattern),
                    func.replace(models.Course.dept_kisaadi, ' ', '').ilike(pattern_nospace),
                    models.Instructor.full_name.ilike(pattern),
                    models.Department.bolum.ilike(pattern)
                )
            )
        
        if term:
            query = query.filter(models.Course.term_id.in_(term))
        if dept:
            clean_depts = [d.strip().upper() for d in dept if d and d.strip()]
            query = query.filter(func.upper(models.Course.dept_kisaadi).in_(clean_depts))
        if instructor:
            if not has_instructor_join:
                query = query.join(models.Instructor)
                has_instructor_join = True
            query = query.filter(func.upper(models.Instructor.full_name) == instructor.strip().upper())
            
        total_hits = query.count()
        
        # Sorting
        if sort_by == "course_code":
            order_col = models.Course.course_code
        elif sort_by == "title":
            order_col = models.Course.title
        elif sort_by == "credits":
            order_col = models.Course.credits
        elif sort_by == "ects":
            order_col = models.Course.ects
        elif sort_by == "term":
            order_col = models.Course.term_id
        elif sort_by == "instructor":
            if not has_instructor_join:
                query = query.outerjoin(models.Instructor)
                has_instructor_join = True
            order_col = models.Instructor.full_name
        else:
            order_col = models.Course.term_id
            
        if sort_by:
            if sort_order == "desc":
                query = query.order_by(order_col.desc(), models.Course.course_code.asc())
            else:
                query = query.order_by(order_col.asc(), models.Course.course_code.asc())
        else:
            # Default sort: term:desc, course_code:asc
            query = query.order_by(models.Course.term_id.desc(), models.Course.course_code.asc())
            
        courses = query.offset(offset).limit(limit).all()
        
        hits = []
        for c in courses:
            slots_data = []
            for s in c.slots:
                slots_data.append({
                    "day_code": s.day_code,
                    "slot_hour": s.slot_hour,
                    "slot_title": s.slot_title,
                    "room_name": s.room.name if s.room else None
                })
            hits.append({
                "id": c.id,
                "course_code": c.course_code,
                "title": c.title,
                "section": c.section,
                "term": c.term_id,
                "department": c.department.bolum if c.department else None,
                "dept_code": c.dept_kisaadi,
                "instructor": c.instructor.full_name if c.instructor else "TBA",
                "instructor_id": c.instructor_id,
                "credits": c.credits,
                "ects": c.ects,
                "delivery_method": c.delivery_method,
                "slots": slots_data
            })
            
        return {
            "hits": hits,
            "offset": offset,
            "limit": limit,
            "estimatedTotalHits": total_hits,
            "totalHits": total_hits,
            "facetDistribution": _get_global_facets_from_db(db)
        }
    except Exception as e:
        logger.error("DB search fallback error: %s", e)
        return {
            "hits": [],
            "offset": offset,
            "limit": limit,
            "estimatedTotalHits": 0,
            "totalHits": 0,
            "facetDistribution": {}
        }

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
    
    upstream_scrape_ts = None
    local_sync_ts = None

    for s in sync_states:
        feed_map[s.feed_name] = {
            "last_cursor": s.last_cursor,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None
        }
        if s.feed_name == "upstream_run" and s.last_cursor:
            upstream_scrape_ts = s.last_cursor
        elif s.feed_name in ("local_sync", "scraper"):
            local_sync_ts = s.last_cursor or (s.updated_at.isoformat() if s.updated_at else None)

    # Fallback to actual data points if upstream_run row is not yet populated
    if not upstream_scrape_ts:
        candidates = []
        if "deltas" in feed_map and feed_map["deltas"]["last_cursor"]:
            candidates.append(feed_map["deltas"]["last_cursor"])
        if "quota_snapshots" in feed_map and feed_map["quota_snapshots"]["last_cursor"]:
            candidates.append(feed_map["quota_snapshots"]["last_cursor"])

        latest_change = db.query(func.max(models.CourseChange.timestamp)).scalar()
        latest_quota = db.query(func.max(models.QuotaSnapshot.captured_at)).scalar()
        if latest_change:
            candidates.append(latest_change)
        if latest_quota:
            candidates.append(latest_quota)

        if candidates:
            upstream_scrape_ts = max(candidates)

    # Calculate staleness (>24 hours)
    is_stale = False
    if upstream_scrape_ts:
        try:
            clean_ts = upstream_scrape_ts.replace("Z", "+00:00")
            ts_dt = datetime.fromisoformat(clean_ts)
            if ts_dt.tzinfo is None:
                ts_dt = ts_dt.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - ts_dt).total_seconds() / 3600
            if age_hours > 24:
                is_stale = True
        except Exception:
            pass
    else:
        is_stale = True

    return {
        "status": "healthy" if not is_stale else "stale",
        "last_scraped_at": upstream_scrape_ts,
        "last_sync_at": local_sync_ts,
        "latest_scrape_time": upstream_scrape_ts,
        "upstream_scrape_time": upstream_scrape_ts,
        "last_sync_time": local_sync_ts,
        "is_stale": is_stale,
        "upstream_run": None,
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
    limit: int = Query(20, ge=0, le=500),
    offset: int = Query(0, ge=0, le=10_000),
    db: Session = Depends(database.get_db)
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
            if d and d.strip():
                clean_d = d.strip().upper()
                escaped = escape_meili_filter(clean_d)
                dept_filters.append(f"dept_code = '{escaped}'")
        if dept_filters:
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
        return MEILI_CLIENT.index('courses').search(q, {
            'filter': " AND ".join(filter_list) if filter_list else None,
            'limit': limit,
            'offset': offset,
            'facets': ['term', 'dept_code', 'instructor', 'delivery_method'],
            'sort': sort_list
        })
    except Exception as e:
        logger.warning("Meilisearch search error, falling back to PostgreSQL: %s", e)
        return _search_courses_from_db(db, q, term, dept, instructor, sort_by, sort_order, limit, offset)

@app.get("/v1/facets")
@cache(expire=3600)
def get_global_facets(db: Session = Depends(database.get_db)):
    try:
        # Return facets for all documents (empty search)
        results = MEILI_CLIENT.index('courses').search("", {
            'facets': ['term', 'dept_code', 'delivery_method'],
            'limit': 0
        })
        facet_dist = results.get('facetDistribution', {})
        if not facet_dist or not facet_dist.get('term'):
            return _get_global_facets_from_db(db)
        return facet_dist
    except Exception as e:
        logger.warning("Meilisearch facets error, falling back to PostgreSQL: %s", e)
        return _get_global_facets_from_db(db)

@app.get("/v1/analytics/ghost-schedule/{term:path}")
@cache(expire=3600)
def get_ghost_schedule(
    term: str, 
    dept: List[str] = Query(None),
    db: Session = Depends(database.get_db)
):
    target_term = term
    if not db.query(models.Course.id).filter(models.Course.term_id == target_term).first():
        if "-" in term and "/" not in term:
            parts = term.rsplit("-", 1)
            if len(parts) == 2 and "-" in parts[0]:
                slash_term = parts[0].replace("-", "/") + "-" + parts[1]
                if db.query(models.Course.id).filter(models.Course.term_id == slash_term).first():
                    target_term = slash_term
        elif "/" in term:
            dash_term = term.replace("/", "-")
            if db.query(models.Course.id).filter(models.Course.term_id == dash_term).first():
                target_term = dash_term

    query = db.query(
        models.CourseSlot.day_code,
        models.CourseSlot.slot_hour,
        models.Room.name.label("room_name"),
        models.Course.course_code,
        models.Course.dept_kisaadi
    ).join(models.Course).join(models.Room).filter(models.Course.term_id == target_term)
    
    if dept:
        clean_depts = [d.strip().upper() for d in dept if d and d.strip()]
        query = query.filter(func.upper(models.Course.dept_kisaadi).in_(clean_depts))
        
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

@app.get("/v1/instructors/{instructor_id}")
@cache(expire=3600)
def get_instructor(instructor_id: int, request: Request = None, db: Session = Depends(database.get_db)):
    instructor = db.query(models.Instructor).filter(models.Instructor.id == instructor_id).first()
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor not found")
    if request:
        accept = request.headers.get("accept", "")
        if "application/ld+json" in accept or "application/json-ld" in accept:
            return JSONResponse(
                content=instructor_to_json_ld(instructor.id, instructor.full_name),
                media_type="application/ld+json"
            )
    return schemas.Instructor.model_validate(instructor).model_dump()

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
@cache(expire=300)
def get_terms(db: Session = Depends(database.get_db)):
    terms = db.query(models.Term).order_by(models.Term.id.desc()).all()
    return [schemas.Term.model_validate(t).model_dump() for t in terms]

@app.get("/v1/departments")
@cache(expire=300)
def get_departments(request: Request = None, db: Session = Depends(database.get_db)):
    depts = db.query(models.Department).order_by(models.Department.kisaadi).all()
    dept_dicts = [schemas.Department.model_validate(d).model_dump() for d in depts]
    if request:
        accept = request.headers.get("accept", "")
        if "application/ld+json" in accept or "application/json-ld" in accept:
            return JSONResponse(
                content=departments_to_json_ld(dept_dicts),
                media_type="application/ld+json"
            )
    return dept_dicts

@app.get("/v1/departments/{dept_code}/unique-courses")
@cache(expire=3600)
def get_department_unique_courses(dept_code: str, db: Session = Depends(database.get_db)):
    clean_dept = dept_code.strip().upper()
    # Query distinct course_code, title, term_id to minimize row transfer and in-memory deduplication
    courses = db.query(
        models.Course.course_code,
        models.Course.title,
        models.Course.term_id
    ).filter(
        func.upper(models.Course.dept_kisaadi) == clean_dept
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
    clean_dept = dept_code.strip().upper()
    results = db.query(
        models.Instructor.id,
        models.Instructor.full_name,
        func.max(models.Course.term_id).label("last_term"),
        func.count(models.Course.id).label("course_count"),
        func.count(func.distinct(models.Course.term_id)).label("total_semesters")
    ).join(models.Course).filter(func.upper(models.Course.dept_kisaadi) == clean_dept).group_by(
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
def get_course_history(course_code: str, request: Request = None, db: Session = Depends(database.get_db)):
    clean_code = " ".join(course_code.strip().split())
    if not clean_code:
        raise HTTPException(status_code=404, detail="Course history not found")
    
    courses = db.query(models.Course).options(
        joinedload(models.Course.instructor),
        joinedload(models.Course.slots).joinedload(models.CourseSlot.room)
    ).filter(
        func.upper(models.Course.course_code) == clean_code.upper()
    ).order_by(models.Course.term_id.desc(), models.Course.section.asc()).limit(1000).all()
    
    if not courses:
        no_spaces = clean_code.replace(" ", "").upper()
        courses = db.query(models.Course).options(
            joinedload(models.Course.instructor),
            joinedload(models.Course.slots).joinedload(models.CourseSlot.room)
        ).filter(
            func.upper(func.replace(models.Course.course_code, ' ', '')) == no_spaces
        ).order_by(models.Course.term_id.desc(), models.Course.section.asc()).limit(1000).all()
        
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
    if request:
        accept = request.headers.get("accept", "")
        if "application/ld+json" in accept or "application/json-ld" in accept:
            return JSONResponse(
                content=course_history_to_json_ld(clean_code, result),
                media_type="application/ld+json"
            )
    return result

@app.get("/v1/courses/{course_code}/schedule.ics")
@cache(expire=3600)
def get_course_schedule_ics_feed(course_code: str, db: Session = Depends(database.get_db)):
    clean_code = " ".join(course_code.strip().split())
    if not clean_code:
        raise HTTPException(status_code=404, detail="Course schedule not found")
    
    courses = db.query(models.Course).options(
        joinedload(models.Course.instructor),
        joinedload(models.Course.slots).joinedload(models.CourseSlot.room)
    ).filter(
        func.upper(models.Course.course_code) == clean_code.upper()
    ).order_by(models.Course.term_id.desc(), models.Course.section.asc()).limit(1000).all()
    
    if not courses:
        no_spaces = clean_code.replace(" ", "").upper()
        courses = db.query(models.Course).options(
            joinedload(models.Course.instructor),
            joinedload(models.Course.slots).joinedload(models.CourseSlot.room)
        ).filter(
            func.upper(func.replace(models.Course.course_code, ' ', '')) == no_spaces
        ).order_by(models.Course.term_id.desc(), models.Course.section.asc()).limit(1000).all()
        
    if not courses:
        raise HTTPException(status_code=404, detail="Course schedule not found")

    history = []
    for c in courses:
        history.append({
            "id": c.id,
            "term_id": c.term_id,
            "section": c.section,
            "title": c.title,
            "instructor": c.instructor.full_name if c.instructor else "TBA",
            "slots": [{
                "day": s.day_code,
                "hour": s.slot_hour,
                "room": s.room.name if s.room else "N/A"
            } for s in c.slots]
        })
    history.sort(key=lambda x: x['term_id'], reverse=True)
    ics_text = generate_course_schedule_ics(clean_code, history)
    safe_filename = clean_code.replace(" ", "_")
    return Response(
        content=ics_text,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="boun_{safe_filename}_schedule.ics"'}
    )

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
        return [schemas.QuotaSnapshot.model_validate(s).model_dump() for s in snapshots]

    try:
        row_num = func.row_number().over(
            partition_by=(models.QuotaSnapshot.section, models.QuotaSnapshot.department),
            order_by=models.QuotaSnapshot.captured_at.desc()
        ).label("rn")

        ranked_subq = query.with_entities(
            models.QuotaSnapshot.id.label("snapshot_id"),
            row_num
        ).subquery()

        snapshots = db.query(models.QuotaSnapshot).join(
            ranked_subq,
            models.QuotaSnapshot.id == ranked_subq.c.snapshot_id
        ).filter(
            ranked_subq.c.rn == 1
        ).all()
    except Exception as e:
        logger.error(f"Failed to query quota snapshots for {clean_code}: {e}")
        raise HTTPException(status_code=500, detail="Database error retrieving quota snapshots")

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

