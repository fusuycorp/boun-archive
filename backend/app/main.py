import asyncio
import hashlib
import json
import logging
import os
import re
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from typing import Any, Literal

import meilisearch
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.coder import JsonCoder
from fastapi_cache.decorator import cache
from meilisearch.errors import MeilisearchApiError
from redis import asyncio as aioredis
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from . import database, models, schemas
from .analytics import MacroEngine
from .optimizer import solve_schedule_csp
from .semantic import (
    course_history_to_json_ld,
    course_history_to_turtle,
    departments_to_json_ld,
    departments_to_turtle,
    generate_course_schedule_ics,
    generate_dcat_catalog_jsonld,
    generate_void_description,
    instructor_to_json_ld,
    instructor_to_turtle,
)
from .sync import (
    apply_deltas_batch,
    ensure_schema_columns,
    record_scrape_summary,
    verify_webhook_signature,
)

ALLOWED_SORTS = {"term", "course_code", "title", "instructor", "credits", "ects"}

logger = logging.getLogger(__name__)

def escape_meili_filter(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")

def escape_sql_wildcards(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

class ResponseAwareJsonCoder(JsonCoder):
    """JSON coder that preserves Starlette Response/JSONResponse media types and headers across cache hits."""

    @classmethod
    def encode(cls, value: Any) -> bytes:
        if isinstance(value, Response):
            body_text = (
                value.body.decode("utf-8")
                if isinstance(value.body, (bytes, bytearray))
                else str(value.body)
            )
            headers = {
                k.decode("latin-1"): v.decode("latin-1")
                for k, v in getattr(value, "raw_headers", [])
                if k.decode("latin-1").lower() not in ("content-length", "content-type")
            }
            return json.dumps(
                {
                    "_cached_starlette_response": True,
                    "content": body_text,
                    "status_code": value.status_code,
                    "media_type": value.media_type,
                    "headers": headers,
                }
            ).encode("utf-8")
        return super().encode(value)

    @classmethod
    def decode(cls, value: bytes) -> Any:
        decoded = super().decode(value)
        if isinstance(decoded, dict):
            if decoded.get("_cached_starlette_response") is True:
                return Response(
                    content=decoded.get("content", ""),
                    status_code=decoded.get("status_code", 200),
                    media_type=decoded.get("media_type"),
                    headers=decoded.get("headers") or {},
                )
            if (
                "status_code" in decoded
                and "media_type" in decoded
                and "body" in decoded
                and "raw_headers" in decoded
            ):
                headers = {
                    k: v
                    for k, v in decoded.get("raw_headers", [])
                    if isinstance(k, str)
                    and k.lower() not in ("content-length", "content-type")
                }
                return Response(
                    content=decoded.get("body", ""),
                    status_code=decoded.get("status_code", 200),
                    media_type=decoded.get("media_type"),
                    headers=headers,
                )
        return decoded


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
    accept_raw = request.headers.get("accept", "") if request and hasattr(request, "headers") else ""
    if "text/turtle" in accept_raw or "application/x-turtle" in accept_raw:
        accept_hdr = "text/turtle"
    elif "application/ld+json" in accept_raw or "application/json-ld" in accept_raw:
        accept_hdr = "application/ld+json"
    else:
        accept_hdr = "application/json"
    cache_key = hashlib.md5(
        f"{func.__module__}:{func.__name__}:{filtered_args}:{filtered_kwargs}:{accept_hdr}".encode()
    ).hexdigest()
    return f"{namespace}:v2:{cache_key}"

def _trigger_initial_meili_sync_if_empty() -> None:
    try:
        stats = MEILI_CLIENT.index("courses").get_stats()
        doc_count = getattr(stats, "number_of_documents", None)
        if doc_count is None and isinstance(stats, dict):
            doc_count = stats.get("numberOfDocuments", 0)
        if doc_count != 0:
            return
        logger.info("Meilisearch 'courses' index has 0 documents. Triggering background sync from PostgreSQL...")
        import sys
        import threading
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


def _init_meilisearch_on_boot() -> None:
    try:
        try:
            MEILI_CLIENT.create_index("courses", {"primaryKey": "id"})
        except MeilisearchApiError as e:
            if e.code != "index_already_exists":
                logger.error("Failed to create Meilisearch 'courses' index: %s", e)

        MEILI_CLIENT.index("courses").update_settings(
            {
                "filterableAttributes": [
                    "term",
                    "dept_code",
                    "department",
                    "instructor",
                    "instructor_id",
                    "delivery_method",
                    "has_syllabus",
                ],
                "searchableAttributes": [
                    "course_code",
                    "title",
                    "instructor",
                    "department",
                    "catalog_text",
                    "syllabus_snippet",
                ],
                "faceting": {"maxValuesPerFacet": 10000},
                "pagination": {"maxTotalHits": 200000},
                "sortableAttributes": ["term", "course_code", "title", "instructor", "credits", "ects"],
            }
        )
        _trigger_initial_meili_sync_if_empty()
    except Exception as e:
        logger.warning("Meilisearch setup/configuration encountered an issue on startup: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis = aioredis.from_url(redis_url, socket_timeout=5, socket_connect_timeout=5)
    FastAPICache.init(
        RedisBackend(redis),
        prefix="fastapi-cache",
        coder=ResponseAwareJsonCoder,
        key_builder=custom_key_builder,
    )

    try:
        await asyncio.to_thread(ensure_schema_columns, database.engine)
    except Exception as e:
        logger.warning("Schema column check skipped on startup: %s", e)

    await asyncio.to_thread(_init_meilisearch_on_boot)

    # Start background scraper sync on boot only if explicitly enabled (sync_worker handles daemon sync in cluster)
    if os.getenv("ENABLE_BOOT_SYNC", "").lower() in ("true", "1", "yes"):
        import threading

        threading.Thread(target=_run_scraper_sync_job, kwargs={"mode": "incremental"}, daemon=True).start()

    try:
        yield
    finally:
        if hasattr(redis, "aclose"):
            await redis.aclose()
        elif hasattr(redis, "close"):
            await redis.close()

def _run_scraper_sync_job(term_id: str | None = None, mode: str = "incremental") -> None:
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
    MEILI_MASTER_KEY,
    timeout=5,
)

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://bountools.com").strip().rstrip("/") or "https://bountools.com"
_MAX_WEBHOOK_BODY_BYTES = 2 * 1024 * 1024

_DB_SORT_COLUMN_MAP = {
    "course_code": models.Course.course_code,
    "title": models.Course.title,
    "credits": models.Course.credits,
    "ects": models.Course.ects,
    "term": models.Course.term_id,
}


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
        syllabus_rows = (
            db.query(models.Course.has_syllabus, func.count(models.Course.id))
            .group_by(models.Course.has_syllabus)
            .all()
        )
        has_syllabus_counts: dict[str, int] = {}
        for flag, count in syllabus_rows:
            key = "true" if flag else "false"
            has_syllabus_counts[key] = has_syllabus_counts.get(key, 0) + count
        instructor_counts = dict(
            db.query(models.Instructor.full_name, func.count(models.Course.id))
            .join(models.Course, models.Course.instructor_id == models.Instructor.id)
            .group_by(models.Instructor.full_name)
            .all()
        )
        return {
            "term": term_counts,
            "dept_code": dept_counts,
            "instructor": instructor_counts,
            "delivery_method": delivery_counts,
            "has_syllabus": has_syllabus_counts,
        }
    except Exception as e:
        logger.error("DB facet fallback error: %s", e)
        raise HTTPException(status_code=503, detail="Database facet service temporarily unavailable")


def _apply_db_search_query_filter(query: Any, q: str) -> tuple[Any, bool]:
    if not q or not q.strip():
        return query, False
    clean_q = escape_sql_wildcards(q.strip())
    clean_q_nospace = clean_q.replace(" ", "")
    pattern = f"%{clean_q}%"
    pattern_nospace = f"%{clean_q_nospace}%"
    query = (
        query.outerjoin(models.Instructor)
        .outerjoin(models.Department)
        .outerjoin(models.CourseCatalog, models.CourseCatalog.course_code == models.Course.course_code)
    )
    query = query.filter(
        or_(
            models.Course.course_code.ilike(pattern, escape="\\"),
            func.replace(models.Course.course_code, " ", "").ilike(pattern_nospace, escape="\\"),
            models.Course.title.ilike(pattern, escape="\\"),
            models.Course.dept_kisaadi.ilike(pattern, escape="\\"),
            func.replace(models.Course.dept_kisaadi, " ", "").ilike(pattern_nospace, escape="\\"),
            models.Instructor.full_name.ilike(pattern, escape="\\"),
            models.Department.bolum.ilike(pattern, escape="\\"),
            models.Course.syllabus_text.ilike(pattern, escape="\\"),
            models.CourseCatalog.canonical_text.ilike(pattern, escape="\\"),
        )
    )
    return query, True


def _apply_db_search_filters(
    query: Any,
    term: list[str] | None,
    dept: list[str] | None,
    instructor: str | None,
    has_syllabus: bool | None,
    has_instructor_join: bool,
) -> tuple[Any, bool]:
    if term:
        clean_terms = [t.strip() for t in term if t and t.strip()]
        if clean_terms:
            query = query.filter(models.Course.term_id.in_(clean_terms))
    if dept:
        clean_depts = [d.strip().upper() for d in dept if d and d.strip()]
        if clean_depts:
            query = query.filter(func.upper(models.Course.dept_kisaadi).in_(clean_depts))
    if instructor:
        if not has_instructor_join:
            query = query.join(models.Instructor)
            has_instructor_join = True
        query = query.filter(func.upper(models.Instructor.full_name) == instructor.strip().upper())
    if has_syllabus is not None:
        query = query.filter(models.Course.has_syllabus.is_(has_syllabus))
    return query, has_instructor_join


def _apply_db_search_sorting(query: Any, sort_by: str | None, sort_order: str, has_instructor_join: bool) -> Any:
    if not sort_by:
        return query.order_by(models.Course.term_id.desc(), models.Course.course_code.asc())
    if sort_by == "instructor":
        if not has_instructor_join:
            query = query.outerjoin(models.Instructor)
        order_col = models.Instructor.full_name
    else:
        order_col = _DB_SORT_COLUMN_MAP.get(sort_by, models.Course.term_id)
    primary = order_col.desc() if sort_order == "desc" else order_col.asc()
    return query.order_by(primary, models.Course.course_code.asc())


def _serialize_db_search_hit(c: models.Course) -> dict:
    return {
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
        "has_syllabus": bool(c.has_syllabus),
        "slots": [
            {
                "day_code": s.day_code,
                "slot_hour": s.slot_hour,
                "slot_title": s.slot_title,
                "room_name": s.room.name if s.room else None,
            }
            for s in c.slots
        ],
    }


def _search_courses_from_db(
    db: Session,
    q: str,
    term: list[str] | None,
    dept: list[str] | None,
    instructor: str | None,
    sort_by: str | None,
    sort_order: str,
    limit: int,
    offset: int,
    has_syllabus: bool | None = None,
) -> dict:
    try:
        query = db.query(models.Course).options(
            joinedload(models.Course.department),
            joinedload(models.Course.instructor),
            selectinload(models.Course.slots).joinedload(models.CourseSlot.room),
        )
        query, has_instructor_join = _apply_db_search_query_filter(query, q)
        query, has_instructor_join = _apply_db_search_filters(
            query, term, dept, instructor, has_syllabus, has_instructor_join
        )
        total_hits = query.count()
        query = _apply_db_search_sorting(query, sort_by, sort_order, has_instructor_join)
        courses = query.offset(offset).limit(limit).all()

        return {
            "hits": [_serialize_db_search_hit(c) for c in courses],
            "offset": offset,
            "limit": limit,
            "estimatedTotalHits": total_hits,
            "totalHits": total_hits,
            "facetDistribution": _get_global_facets_from_db(db),
        }
    except Exception as e:
        logger.error("DB search fallback error: %s", e)
        raise HTTPException(status_code=503, detail="Search fallback service temporarily unavailable")

@app.get("/")
def read_root():
    return {"message": "Welcome to the BOUN Archive API"}

@app.get("/health")
@app.head("/health")
def health_check():
    return {"status": "healthy"}

def _resolve_fallback_scrape_ts(db: Session, feed_map: dict[str, dict[str, Any]]) -> str | None:
    candidates: list[str] = []
    for feed_name in ("deltas", "quota_snapshots"):
        cursor_val = (feed_map.get(feed_name) or {}).get("last_cursor")
        if cursor_val:
            candidates.append(cursor_val)
    for scalar in (
        db.query(func.max(models.CourseChange.timestamp)).scalar(),
        db.query(func.max(models.QuotaSnapshot.captured_at)).scalar(),
    ):
        if scalar:
            candidates.append(scalar)
    return max(candidates) if candidates else None


def _is_timestamp_stale(ts_str: str | None) -> bool:
    if not ts_str:
        return True
    try:
        ts_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        if ts_dt.tzinfo is None:
            ts_dt = ts_dt.replace(tzinfo=UTC)
        return (datetime.now(UTC) - ts_dt).total_seconds() / 3600 > 24
    except Exception:
        return True


@app.get("/v1/system/status", response_model=schemas.SystemStatusResponse)
@app.get("/v1/sync/status", response_model=schemas.SystemStatusResponse)
@cache(expire=30)
def get_system_status(db: Session = Depends(database.get_db)):
    sync_states = db.query(models.SyncState).all()
    feed_map: dict[str, dict[str, Any]] = {}
    upstream_scrape_ts: str | None = None
    local_sync_ts: str | None = None

    for s in sync_states:
        updated_iso = s.updated_at.isoformat() if s.updated_at else None
        feed_map[s.feed_name] = {"last_cursor": s.last_cursor, "updated_at": updated_iso}
        if s.feed_name == "upstream_run" and s.last_cursor:
            upstream_scrape_ts = s.last_cursor
        elif s.feed_name in ("local_sync", "scraper"):
            local_sync_ts = s.last_cursor or updated_iso

    if not upstream_scrape_ts:
        upstream_scrape_ts = _resolve_fallback_scrape_ts(db, feed_map)

    is_stale = _is_timestamp_stale(upstream_scrape_ts)
    return {
        "status": "healthy" if not is_stale else "stale",
        "last_scraped_at": upstream_scrape_ts,
        "last_sync_at": local_sync_ts,
        "latest_scrape_time": upstream_scrape_ts,
        "upstream_scrape_time": upstream_scrape_ts,
        "last_sync_time": local_sync_ts,
        "is_stale": is_stale,
        "upstream_run": None,
        "feeds": feed_map,
    }

def _meili_or_clause(field: str, values: list[str], uppercase: bool = False) -> str | None:
    terms: list[str] = []
    for raw in values:
        cleaned = raw.strip() if raw else ""
        if not cleaned:
            continue
        val = cleaned.upper() if uppercase else raw
        terms.append(f"{field} = '{escape_meili_filter(val)}'")
    return f"({' OR '.join(terms)})" if terms else None


def _build_meili_filter(
    term: list[str] | None,
    dept: list[str] | None,
    instructor: str | None,
    has_syllabus: bool | None,
) -> str | None:
    filter_list: list[str] = []
    if term:
        clause = _meili_or_clause("term", term, uppercase=False)
        if clause:
            filter_list.append(clause)
    if dept:
        clause = _meili_or_clause("dept_code", dept, uppercase=True)
        if clause:
            filter_list.append(clause)
    if instructor:
        filter_list.append(f"instructor = '{escape_meili_filter(instructor)}'")
    if has_syllabus is not None:
        filter_list.append(f"has_syllabus = {'true' if has_syllabus else 'false'}")
    return " AND ".join(filter_list) if filter_list else None


def _build_meili_sort(sort_by: str | None, sort_order: str) -> list[str]:
    if not sort_by:
        return ["term:desc", "course_code:asc"]
    if sort_by not in ALLOWED_SORTS:
        raise HTTPException(status_code=422, detail=f"sort_by must be one of {sorted(ALLOWED_SORTS)}")
    return [f"{sort_by}:{sort_order}"]


@app.get("/v1/search")
@cache(expire=600)
def search_courses(
    q: str = "",
    term: list[str] = Query(None),
    dept: list[str] = Query(None),
    instructor: str | None = None,
    has_syllabus: bool | None = Query(None),
    sort_by: str | None = Query(None),
    sort_order: Literal["asc", "desc"] = "asc",
    limit: int = Query(20, ge=0, le=500),
    offset: int = Query(0, ge=0, le=10_000),
    db: Session = Depends(database.get_db),
):
    meili_filter = _build_meili_filter(term, dept, instructor, has_syllabus)
    sort_list = _build_meili_sort(sort_by, sort_order)

    try:
        return MEILI_CLIENT.index("courses").search(
            q,
            {
                "filter": meili_filter,
                "limit": limit,
                "offset": offset,
                "facets": ["term", "dept_code", "instructor", "delivery_method", "has_syllabus"],
                "sort": sort_list,
            },
        )
    except MeilisearchApiError as e:
        if e.code == "index_not_found":
            logger.warning("Meilisearch index 'courses' not ready during search; raising 503 to avoid caching empty state")
            raise HTTPException(status_code=503, detail="Search index is initializing")
        logger.warning("Meilisearch API error, falling back to PostgreSQL: %s", e)
        return _search_courses_from_db(
            db, q, term, dept, instructor, sort_by, sort_order, limit, offset, has_syllabus=has_syllabus
        )
    except Exception as e:
        logger.warning("Meilisearch search error, falling back to PostgreSQL: %s", e)
        return _search_courses_from_db(
            db, q, term, dept, instructor, sort_by, sort_order, limit, offset, has_syllabus=has_syllabus
        )

@app.get("/v1/facets")
@cache(expire=3600)
def get_global_facets(db: Session = Depends(database.get_db)):
    try:
        # Return facets for all documents (empty search)
        results = MEILI_CLIENT.index('courses').search("", {
            'facets': ['term', 'dept_code', 'delivery_method', 'has_syllabus'],
            'limit': 0
        })
        facet_dist = results.get('facetDistribution', {})
        if not facet_dist or not facet_dist.get('term'):
            facets_from_db = _get_global_facets_from_db(db)
            if not facets_from_db or not facets_from_db.get('term'):
                raise HTTPException(status_code=503, detail="Search facets temporarily unavailable")
            return facets_from_db
        return facet_dist
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Meilisearch facets error, falling back to PostgreSQL: %s", e)
        facets_from_db = _get_global_facets_from_db(db)
        if not facets_from_db or not facets_from_db.get('term'):
            raise HTTPException(status_code=503, detail="Search facets temporarily unavailable")
        return facets_from_db

# Canonical Building and Campus Topology for Boğaziçi University
# Invariant: JF (John Freely Hall) is in Güney, EF (Education Faculty) is in Kuzey, HH (Hamlin Hall) is in Güney
ROOM_LOCATION_REGISTRY = {
    # Kuzey Kampüs (North)
    "EF": ("Education Faculty", "Kuzey"),
    "NH": ("New Hall", "Kuzey"),
    "KB": ("Kare Blok", "Kuzey"),
    "KBPCLAB": ("Kare Blok PC Lab", "Kuzey"),
    "KBZ": ("Kare Blok Basement", "Kuzey"),
    "BM": ("Computer Engineering", "Kuzey"),
    "ETA": ("ETA Building", "Kuzey"),
    "ETAB": ("ETA Building Block B", "Kuzey"),
    "ETB": ("ETA Building Block B", "Kuzey"),
    "ET": ("ETA Building", "Kuzey"),
    "KP": ("Kuzey Park", "Kuzey"),
    "KPARK": ("Kuzey Park", "Kuzey"),
    "PARK": ("Kuzey Park", "Kuzey"),
    "PARK1": ("Kuzey Park", "Kuzey"),
    "PARK2": ("Kuzey Park", "Kuzey"),
    "VY": ("Vedat Yerlici", "Kuzey"),
    "VYKM": ("Vedat Yerlici Center", "Kuzey"),
    "VB": ("Vedat Yerlici", "Kuzey"),
    "KYD": ("Kuzey YADYOK", "Kuzey"),
    "SL": ("Student Labs", "Kuzey"),
    "BİM": ("Bilgi İşlem Merkezi", "Kuzey"),
    "BIM": ("Bilgi İşlem Merkezi", "Kuzey"),
    "KGYM": ("Kuzey Spor Salonu", "Kuzey"),

    # Güney Kampüs (South)
    "JF": ("John Freely Hall", "Güney"),
    "HH": ("Hamlin Hall", "Güney"),
    "HAMLİN": ("Hamlin Hall", "Güney"),
    "HAMLIN": ("Hamlin Hall", "Güney"),
    "TB": ("Basic Sciences (Anderson)", "Güney"),
    "TBA": ("Anderson Hall", "Güney"),
    "TBD": ("Basic Sciences Block D", "Güney"),
    "AND": ("Anderson Hall", "Güney"),
    "IB": ("Washburn Hall (İİBF)", "Güney"),
    "İB": ("Washburn Hall (İİBF)", "Güney"),
    "İBRAHİM": ("İbrahim Bodur Oditoryumu", "Güney"),
    "IBRAHIM": ("İbrahim Bodur Oditoryumu", "Güney"),
    "M": ("Engineering Building", "Güney"),
    "NB": ("Natuk Birkan", "Güney"),
    "NBB": ("Natuk Birkan Block B", "Güney"),
    "NBZ": ("Natuk Birkan Basement", "Güney"),
    "ALH": ("Albert Long Hall", "Güney"),
    "DODGE": ("Dodge Hall Gym", "Güney"),
    "DOGE": ("Dodge Hall Gym", "Güney"),
    "SOC": ("Sociology Seminar Rooms", "Güney"),
    "ATA": ("Atatürk Institute", "Güney"),
    "GYD": ("Güney YADYOK", "Güney"),
    "SC": ("Science Hall", "Güney"),
    "FED": ("Arts & Sciences", "Güney"),
    "ÖFB": ("Öğrenci Faaliyetleri Binası", "Güney"),
    "OFB": ("Öğrenci Faaliyetleri Binası", "Güney"),
    "ÖZGER": ("Özger Arnas Salonu", "Güney"),
    "OZGER": ("Özger Arnas Salonu", "Güney"),
    "HÜLYA": ("Hülya Sanat Atölyesi", "Güney"),
    "HULYA": ("Hülya Sanat Atölyesi", "Güney"),
    "REVİR": ("Güney Revir", "Güney"),
    "REVIR": ("Güney Revir", "Güney"),
    "GÜNEY": ("Güney Kampüs", "Güney"),
    "GUNEY": ("Güney Kampüs", "Güney"),

    # Hisar Kampüs
    "HKB": ("Hisar Campus Block B", "Hisar"),
    "HKC": ("Hisar Campus Block C", "Hisar"),
    "HKA": ("Hisar Campus Block A", "Hisar"),
    "HKD": ("Hisar Campus Block D", "Hisar"),
    "HB": ("Hisar Block B", "Hisar"),
    "HC": ("Hisar Block C", "Hisar"),
    "HA": ("Hisar Block A", "Hisar"),
    "HD": ("Hisar Block D", "Hisar"),
    "HİSAR": ("Hisar Campus", "Hisar"),
    "HISAR": ("Hisar Campus", "Hisar"),

    # Uçaksavar Kampüs
    "GKM": ("Garanti Culture Center", "Uçaksavar"),
    "AYHAN": ("Ayhan Şahenk Salonu", "Uçaksavar"),
    "UÇAKSAVAR": ("Uçaksavar Athletic Field", "Uçaksavar"),
    "UÇAKS": ("Uçaksavar Athletic Field", "Uçaksavar"),
    "PARKE": ("Uçaksavar Spor Salonu", "Uçaksavar"),

    # Kandilli Kampüs
    "KANDİLLİ": ("Kandilli Observatory", "Kandilli"),
    "KANDILLI": ("Kandilli Observatory", "Kandilli"),
    "KOERI": ("Kandilli Observatory", "Kandilli"),
    "BME": ("Biomedical Institute", "Kandilli"),
    "AZ": ("Aziz Sancar Binası (BME)", "Kandilli"),

    # Sarıtepe Kampüs (Kilyos)
    "KLY": ("Sarıtepe Prep Hall", "Kilyos"),
    "KİLYOS": ("Sarıtepe Campus", "Kilyos"),
    "KILYOS": ("Sarıtepe Campus", "Kilyos"),
    "YYD": ("Sarıtepe YADYOK", "Kilyos"),
}

_VIRTUAL_KEYWORDS = ("ONLINE", "UZAKTAN", "VIRTUAL", "WEB", "ZOOM")

_BUILDING_CAMPUS_RULES = (
    ("Kuzey", ("NEW HALL", "KARE", "EDUCATION", "EĞİTİM", "KUZEY", "COMPUTER", "ETA", "YERLICI", "BİM")),
    ("Güney", ("FREELY", "JOHN", "ANDERSON", "WASHBURN", "ENGINEERING", "NATUK", "HAMLIN", "GÜNEY", "SOUTH")),
    ("Hisar", ("HISAR", "HİSAR")),
    ("Uçaksavar", ("UÇAKSAVAR", "GARANTI", "ŞAHENK")),
    ("Kandilli", ("KANDİLLİ", "KANDILLI")),
    ("Kilyos", ("KİLYOS", "KILYOS", "SARITEPE")),
)

_PREFIX_CAMPUS_RULES = (
    ("Güney", "Hamlin Hall", ("HH", "HAML", "HÜL", "HUL"), ()),
    ("Hisar", "Hisar Building", ("HK", "HB", "HC", "HA", "HD", "HİS", "HIS"), ()),
    ("Kandilli", "Kandilli Building", ("BME", "KOERI", "KAND"), ()),
    ("Kilyos", "Sarıtepe Building", ("KLY", "KİL", "KIL"), ()),
    ("Kuzey", "Kuzey Building", ("EF", "NH", "BM", "ETA", "VY", "K"), ("BME", "KAND", "KOERI", "KLY", "KİL", "KIL")),
    ("Güney", "Güney Building", ("M", "T", "JF", "İB", "IB", "NB"), ("MBG",)),
)


def _infer_campus_from_building(b_clean: str) -> str:
    b_upper = b_clean.upper()
    for campus_name, keywords in _BUILDING_CAMPUS_RULES:
        if any(w in b_upper for w in keywords):
            return campus_name
    return "Other"


def _infer_campus_from_prefix(upper: str, clean: str) -> tuple[str, str] | None:
    for campus_name, label, prefixes, excluded in _PREFIX_CAMPUS_RULES:
        if excluded and upper.startswith(excluded):
            continue
        if upper.startswith(prefixes):
            return (f"{label} ({clean})", campus_name)
    return None


def resolve_room_location(room_name: str | None, building: str | None = None) -> tuple[str, str]:
    clean = (room_name or "").strip()
    b_clean = (building or "").strip()
    if not clean or clean.upper() in ("TBA", "N/A"):
        if b_clean:
            return (b_clean, _infer_campus_from_building(b_clean))
        return ("TBA" if clean.upper() == "TBA" else "Unassigned / Other", "Other")
    upper = clean.upper()
    if any(tag in upper for tag in _VIRTUAL_KEYWORDS):
        return ("Online / Remote", "Virtual")

    match = re.match(r"^([A-Za-zÇĞİÖŞÜçğıöşü]+)", clean)
    if match:
        prefix = match.group(1).upper()
        # Only match "TBA" to Anderson Hall when followed by room digits/block (e.g. "TBA 101"), never bare "TBA".
        if prefix != "TBA" or any(ch.isdigit() for ch in clean):
            reg = ROOM_LOCATION_REGISTRY.get(prefix)
            if reg:
                return (b_clean or reg[0], reg[1])

    if b_clean:
        return (b_clean, _infer_campus_from_building(b_clean))

    return _infer_campus_from_prefix(upper, clean) or (
        f"Building {match.group(1).upper()}" if match else "Unassigned / Other",
        "Other",
    )


def _is_assigned_room(room_name: str | None) -> bool:
    return bool(room_name and room_name.strip().upper() not in ("", "N/A", "TBA"))


def _resolve_existing_term_id(db: Session, term: str) -> str:
    if db.query(models.Course.id).filter(models.Course.term_id == term).first():
        return term
    if "-" in term and "/" not in term:
        parts = term.rsplit("-", 1)
        if len(parts) == 2 and "-" in parts[0]:
            slash_term = f"{parts[0].replace('-', '/')}-{parts[1]}"
            if db.query(models.Course.id).filter(models.Course.term_id == slash_term).first():
                return slash_term
    if "/" in term:
        dash_term = term.replace("/", "-")
        if db.query(models.Course.id).filter(models.Course.term_id == dash_term).first():
            return dash_term
    return term


def _same_session_title(title_a: str | None, title_b: str | None) -> bool:
    a = (title_a or "").strip().lower()
    b = (title_b or "").strip().lower()
    if not a or not b:
        return True
    return a == b


def _forward_fill_day_slots(day_code: str, slots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    slots.sort(key=lambda s: (s["slot_hour"] if s["slot_hour"] is not None else 0, (s.get("slot_title") or "").lower()))
    curr_room: str | None = None
    curr_bldg: str | None = None
    curr_hour: int | None = None
    curr_title: str | None = None
    expanded: list[dict[str, Any]] = []

    for s in slots:
        hr = s["slot_hour"]
        r_name = s["room_name"]
        s_title = s.get("slot_title")
        is_contiguous = (
            curr_room
            and hr is not None
            and curr_hour is not None
            and hr == curr_hour + 1
            and _same_session_title(curr_title, s_title)
        )
        if not _is_assigned_room(r_name) and is_contiguous:
            r_name = curr_room
            s["room_name"] = curr_room
            s["building"] = curr_bldg
        elif _is_assigned_room(r_name):
            curr_room = r_name
            curr_bldg = s["building"]
            curr_title = s_title
        elif curr_hour != hr:
            curr_room = None
            curr_bldg = None
            curr_title = s_title
        curr_hour = hr

        if _is_assigned_room(r_name):
            bldg, cmp_name = resolve_room_location(r_name, s["building"])
            expanded.append(
                {
                    "day_code": day_code,
                    "slot_hour": hr,
                    "room_name": r_name,
                    "building": bldg,
                    "campus": cmp_name,
                    "course_code": s["course_code"],
                    "dept_kisaadi": s["dept_kisaadi"],
                }
            )
    return expanded


def _expand_contiguous_room_slots(results: list[Any]) -> list[dict[str, Any]]:
    """Forward-fill rooms across contiguous multi-hour slots per (course_id, day_code)."""
    course_day_slots: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for r in results:
        course_day_slots.setdefault((r.course_id, r.day_code), []).append(
            {
                "slot_hour": r.slot_hour,
                "slot_title": r.slot_title,
                "room_name": r.room_name,
                "building": r.building,
                "course_code": r.course_code,
                "dept_kisaadi": r.dept_kisaadi,
            }
        )
    payload: list[dict[str, Any]] = []
    for (_, d_code), slots in course_day_slots.items():
        payload.extend(_forward_fill_day_slots(d_code, slots))
    return payload


def _filter_ghost_payload(
    payload: list[dict[str, Any]], building: list[str] | None, campus: list[str] | None
) -> list[dict[str, Any]]:
    if building:
        clean_b = {b.strip().lower() for b in building if b and b.strip()}
        payload = [item for item in payload if item["building"].lower() in clean_b]
    if campus:
        clean_c = {c.strip().lower() for c in campus if c and c.strip()}
        payload = [item for item in payload if item["campus"].lower() in clean_c]
    return payload


@app.get("/v1/analytics/ghost-schedule/{term:path}")
@cache(expire=3600)
def get_ghost_schedule(
    term: str,
    dept: list[str] = Query(None),
    building: list[str] = Query(None),
    campus: list[str] = Query(None),
    db: Session = Depends(database.get_db),
):
    target_term = _resolve_existing_term_id(db, term)
    query = (
        db.query(
            models.CourseSlot.course_id,
            models.CourseSlot.day_code,
            models.CourseSlot.slot_hour,
            models.CourseSlot.slot_title,
            models.Room.name.label("room_name"),
            models.Room.building.label("building"),
            models.Course.course_code,
            models.Course.dept_kisaadi,
        )
        .join(models.Course)
        .outerjoin(models.Room)
        .filter(models.Course.term_id == target_term)
    )
    if dept:
        clean_depts = [d.strip().upper() for d in dept if d and d.strip()]
        query = query.filter(func.upper(models.Course.dept_kisaadi).in_(clean_depts))

    payload = _expand_contiguous_room_slots(query.all())
    return _filter_ghost_payload(payload, building, campus)

# Macro Analytics Endpoints
@app.get("/v1/analytics/macro/departments-evolution")
@cache(expire=86400)
def get_dept_evolution(db: Session = Depends(database.get_db)):
    return MacroEngine.get_department_evolution(db)

@app.get("/v1/analytics/macro/scheduling-heatmap")
@cache(expire=86400)
def get_heatmap(decade: int | None = Query(None, ge=1000, le=9999), db: Session = Depends(database.get_db)):
    return MacroEngine.get_scheduling_heatmap(db, decade)

@app.get("/v1/courses/catalog/{course_code}", response_model=schemas.CourseCatalogResponse)
@cache(expire=3600)
def get_course_catalog(course_code: str, db: Session = Depends(database.get_db)):
    clean_code = " ".join(course_code.strip().split())
    if not clean_code:
        raise HTTPException(status_code=404, detail="Course catalog not found")

    entry = (
        db.query(models.CourseCatalog)
        .filter(func.upper(models.CourseCatalog.course_code) == clean_code.upper())
        .first()
    )
    if not entry:
        no_spaces = clean_code.replace(" ", "").upper()
        entry = (
            db.query(models.CourseCatalog)
            .filter(func.upper(func.replace(models.CourseCatalog.course_code, " ", "")) == no_spaces)
            .first()
        )
    if not entry:
        return schemas.CourseCatalogResponse(course_code=clean_code, found=False).model_dump()
    return schemas.CourseCatalogResponse(
        course_code=entry.course_code,
        found=True,
        title=entry.title,
        en_url=entry.en_url,
        tr_url=entry.tr_url,
        en_text=entry.en_text,
        tr_text=entry.tr_text,
        canonical_text=entry.canonical_text,
        updated_at=entry.updated_at,
    ).model_dump()


@app.get("/v1/courses/{course_id}/syllabus-text", response_model=schemas.CourseSyllabusResponse)
@cache(expire=3600)
def get_course_syllabus_text(course_id: int, db: Session = Depends(database.get_db)):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return schemas.CourseSyllabusResponse(
        course_id=course.id,
        term_id=course.term_id,
        course_code=course.course_code,
        section=course.section,
        has_syllabus=bool(course.has_syllabus),
        syllabus_url=course.syllabus_url,
        desc_url=course.desc_url,
        syllabus_text=course.syllabus_text or "",
    ).model_dump()


@app.get("/v1/courses/{course_id}", response_model=schemas.Course)
@cache(expire=3600)
def get_course(course_id: int, db: Session = Depends(database.get_db)):
    course = db.query(models.Course).options(
        joinedload(models.Course.instructor),
        joinedload(models.Course.slots).joinedload(models.CourseSlot.room)
    ).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return schemas.Course.model_validate(course).model_dump()

@app.get("/v1/instructors", response_model=list[schemas.Instructor])
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
        if "text/turtle" in accept or "application/x-turtle" in accept:
            return Response(
                content=instructor_to_turtle(instructor.id, instructor.full_name),
                media_type="text/turtle; charset=utf-8"
            )
        if "application/ld+json" in accept or "application/json-ld" in accept:
            return JSONResponse(
                content=instructor_to_json_ld(instructor.id, instructor.full_name),
                media_type="application/ld+json"
            )
    return schemas.Instructor.model_validate(instructor).model_dump()

def _summarize_instructor_courses(rows: list[Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summary: dict[str, dict[str, Any]] = {}
    history: list[dict[str, Any]] = []
    for term_id, course_code, section, title in rows:
        code = " ".join((course_code or "").split())
        sec = section.strip() if section else None
        history.append({"term": term_id, "course_code": code, "section": sec, "title": title})
        if not code:
            continue
        entry = summary.setdefault(
            code,
            {"course_code": code, "title": title or "", "sections": set(), "terms": set(), "latest_term": term_id or "", "count": 0},
        )
        if sec:
            entry["sections"].add(sec)
        if term_id:
            entry["terms"].add(term_id)
            if not entry["latest_term"] or term_id > entry["latest_term"]:
                entry["latest_term"] = term_id
                if title:
                    entry["title"] = title
        entry["count"] += 1

    unique_courses = [
        {
            "course_code": v["course_code"],
            "title": v["title"],
            "sections": sorted(v["sections"]),
            "terms_count": len(v["terms"]),
            "latest_term": v["latest_term"],
            "total_offerings": v["count"],
        }
        for v in sorted(summary.values(), key=lambda x: x["count"], reverse=True)
    ]
    history.sort(key=lambda x: (x["term"] or "", x["course_code"] or "", x["section"] or ""), reverse=True)
    return unique_courses, history


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

    course_rows = (
        db.query(
            models.Course.term_id,
            models.Course.course_code,
            models.Course.section,
            models.Course.title,
        )
        .filter(models.Course.instructor_id == instructor_id)
        .all()
    )
    total_semesters = len({r.term_id for r in course_rows})
    unique_courses, history = _summarize_instructor_courses(course_rows)

    return {
        "instructor_name": instructor.full_name,
        "total_semesters_taught": total_semesters,
        "total_courses_taught": len(course_rows),
        "most_frequent_courses": most_frequent,
        "preferred_slots": slots_count,
        "courses_summary": unique_courses,
        "history": history,
    }

@app.get("/v1/terms", response_model=list[schemas.Term])
@cache(expire=300)
def get_terms(db: Session = Depends(database.get_db)):
    terms = db.query(models.Term).order_by(models.Term.id.desc()).all()
    return [schemas.Term.model_validate(t).model_dump() for t in terms]

@app.get("/v1/departments")
@cache(expire=300)
def get_departments(request: Request = None, db: Session = Depends(database.get_db)):
    depts = db.query(models.Department).order_by(models.Department.kisaadi).all()
    valid_depts = [d for d in depts if d.kisaadi and not any(ch.isdigit() for ch in d.kisaadi)]
    dept_dicts = [schemas.Department.model_validate(d).model_dump() for d in valid_depts]
    if request:
        accept = request.headers.get("accept", "")
        if "text/turtle" in accept or "application/x-turtle" in accept:
            return Response(
                content=departments_to_turtle(dept_dicts),
                media_type="text/turtle; charset=utf-8"
            )
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
        if term_id and term_id not in unique_courses[code]["terms"]:
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
        selectinload(models.Course.slots).joinedload(models.CourseSlot.room)
    ).filter(
        func.upper(models.Course.course_code) == clean_code.upper()
    ).order_by(models.Course.term_id.desc(), models.Course.section.asc()).limit(1000).all()
    
    if not courses:
        no_spaces = clean_code.replace(" ", "").upper()
        courses = db.query(models.Course).options(
            joinedload(models.Course.instructor),
            selectinload(models.Course.slots).joinedload(models.CourseSlot.room)
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
            "instructor_id": c.instructor_id,
            "credits": c.credits,
            "ects": c.ects,
            "delivery_method": c.delivery_method,
            "has_syllabus": bool(c.has_syllabus),
            "syllabus_url": c.syllabus_url,
            "desc_url": c.desc_url,
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
        if "text/turtle" in accept or "application/x-turtle" in accept:
            return Response(
                content=course_history_to_turtle(clean_code, result),
                media_type="text/turtle; charset=utf-8"
            )
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
        selectinload(models.Course.slots).joinedload(models.CourseSlot.room)
    ).filter(
        func.upper(models.Course.course_code) == clean_code.upper()
    ).order_by(models.Course.term_id.desc(), models.Course.section.asc()).limit(1000).all()
    
    if not courses:
        no_spaces = clean_code.replace(" ", "").upper()
        courses = db.query(models.Course).options(
            joinedload(models.Course.instructor),
            selectinload(models.Course.slots).joinedload(models.CourseSlot.room)
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

@app.get("/v1/courses/{course_code}/quota", response_model=list[schemas.QuotaSnapshot])
@cache(expire=60)
def get_course_quota(
    course_code: str,
    term: str | None = Query(None),
    history: bool = Query(False),
    db: Session = Depends(database.get_db)
):
    clean_code = " ".join(course_code.strip().split())
    if not clean_code:
        return []
    nospace_code = clean_code.replace(" ", "").upper()
    code_match = or_(
        func.upper(models.QuotaSnapshot.course_code) == clean_code.upper(),
        func.upper(func.replace(models.QuotaSnapshot.course_code, " ", "")) == nospace_code,
    )

    target_term = _resolve_existing_term_id(db, term.strip()) if term and term.strip() else None
    if not target_term:
        latest_term = db.query(models.QuotaSnapshot.term_id).filter(
            code_match
        ).order_by(models.QuotaSnapshot.term_id.desc()).first()
        if latest_term:
            target_term = latest_term[0]

    query = db.query(models.QuotaSnapshot).filter(code_match)
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

@app.get("/v1/courses/{course_code}/changes", response_model=list[schemas.CourseChange])
@cache(expire=60)
def get_course_changes(
    course_code: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(database.get_db)
):
    clean_code = " ".join(course_code.strip().split())
    if not clean_code:
        return []
    nospace_code = clean_code.replace(" ", "").upper()

    changes = db.query(models.CourseChange).filter(
        or_(
            func.upper(models.CourseChange.course_code) == clean_code.upper(),
            func.upper(func.replace(models.CourseChange.course_code, " ", "")) == nospace_code,
        )
    ).order_by(
        models.CourseChange.timestamp.desc()
    ).limit(limit).all()

    return [schemas.CourseChange.model_validate(c).model_dump() for c in changes]

@app.get("/.well-known/void")
@app.get("/v1/void.ttl")
@cache(expire=86400)
def get_void_dataset_description():
    return Response(
        content=generate_void_description(base_url=PUBLIC_BASE_URL),
        media_type="text/turtle; charset=utf-8",
        headers={"Vary": "Accept"},
    )

@app.get("/v1/catalog.jsonld")
@cache(expire=86400)
def get_dcat_catalog():
    return JSONResponse(
        content=generate_dcat_catalog_jsonld(base_url=PUBLIC_BASE_URL),
        media_type="application/ld+json",
        headers={"Vary": "Accept"},
    )

@app.post("/v1/optimizer/schedule", response_model=schemas.ScheduleOptimizationResponse)
def optimize_schedule(
    request: schemas.ScheduleOptimizationRequest,
    db: Session = Depends(database.get_db)
):
    """
    Deterministic Constraint Satisfaction Problem (CSP) schedule solver.
    Evaluates all section slot permutations, eliminates conflicts, and optimizes
    for minimal gap hours, reduced campus days, and confirmed instructors.
    """
    return solve_schedule_csp(db=db, request=request)


async def _clear_fastapi_cache_safely() -> None:
    with suppress(Exception):
        await FastAPICache.clear()


def _parse_webhook_deltas(payload: Any) -> list[dict[str, Any]]:
    deltas = payload.get("deltas") if isinstance(payload, dict) and "deltas" in payload else payload
    if isinstance(deltas, list):
        return deltas
    return [deltas] if isinstance(deltas, dict) else []


@app.post("/v1/webhooks/scraper")
async def handle_scraper_webhook(
    request: Request,
    db: Session = Depends(database.get_db),
):
    """
    Real-time webhook ingestion endpoint for upstream boun-scrape events.
    Receives and processes HMAC-SHA256 signed delta change events and scrape completion summaries.
    """
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > _MAX_WEBHOOK_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Webhook payload exceeds 2 MiB limit")

    raw_body = await request.body()
    if len(raw_body) > _MAX_WEBHOOK_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Webhook payload exceeds 2 MiB limit")

    signature = request.headers.get("x-boun-signature")
    secret = os.getenv("WEBHOOK_SECRET")
    if not verify_webhook_signature(raw_body, signature, secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Malformed JSON payload: {e}")

    event_type = request.headers.get("x-boun-event") or (payload.get("event") if isinstance(payload, dict) else "")

    meili_index = None
    with suppress(Exception):
        meili_index = MEILI_CLIENT.index("courses")

    # 1. Delta Changes Event
    if event_type == "courses.deltas" or (isinstance(payload, dict) and "deltas" in payload):
        deltas = _parse_webhook_deltas(payload)
        touched_ids = await asyncio.to_thread(
            apply_deltas_batch,
            db,
            deltas,
            meili_index,
            False,
        )
        await _clear_fastapi_cache_safely()
        return {
            "status": "ok",
            "event": "courses.deltas",
            "received_count": len(deltas),
            "touched_courses": len(touched_ids),
            "touched_course_ids": touched_ids,
        }

    # 2. Scrape Completion Summary Event
    if event_type == "scrape.summary" or (isinstance(payload, dict) and "run_id" in payload and "status" in payload):
        await asyncio.to_thread(record_scrape_summary, db, payload, False)
        if payload.get("changes_detected", 0) > 0:
            await _clear_fastapi_cache_safely()
        return {
            "status": "ok",
            "event": "scrape.summary",
            "run_id": payload.get("run_id"),
            "term": payload.get("term"),
            "changes_detected": payload.get("changes_detected"),
        }

    # 3. Direct Single Delta (fallback)
    if isinstance(payload, dict) and payload.get("change_type") and payload.get("course_code"):
        touched_ids = await asyncio.to_thread(
            apply_deltas_batch,
            db,
            [payload],
            meili_index,
            False,
        )
        await _clear_fastapi_cache_safely()
        return {
            "status": "ok",
            "event": "course.delta",
            "touched_courses": len(touched_ids),
            "touched_course_ids": touched_ids,
        }

    return {
        "status": "ignored",
        "detail": f"Unrecognized webhook event type: '{event_type}'",
    }


@app.get("/v1/system/sync-status")
def get_sync_status(db: Session = Depends(database.get_db)):
    """
    Integration observability endpoint reporting health, cursors, and lag.
    """
    total_courses = db.query(func.count(models.Course.id)).scalar() or 0
    total_terms = db.query(func.count(models.Term.id)).scalar() or 0
    total_depts = db.query(func.count(models.Department.kisaadi)).scalar() or 0
    latest_term = db.query(models.Term).order_by(models.Term.id.desc()).first()

    sync_states = db.query(models.SyncState).all()
    cursors = {
        s.feed_name: {
            "last_cursor": s.last_cursor,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None
        }
        for s in sync_states
    }

    scraper_url = os.getenv("SCRAPER_API_URL", "https://scraper.bountools.com/api/v1")

    return {
        "status": "healthy",
        "service": "boun-archive",
        "timestamp": datetime.now(UTC).isoformat(),
        "upstream_scraper": {
            "url": scraper_url,
        },
        "database": {
            "total_courses": total_courses,
            "total_terms": total_terms,
            "total_departments": total_depts,
            "latest_term": latest_term.id if latest_term else None,
        },
        "cursors": cursors
    }


