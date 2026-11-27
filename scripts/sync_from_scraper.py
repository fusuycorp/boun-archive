import argparse
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import joinedload, selectinload, sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pathutil import add_import_paths

add_import_paths()

import meilisearch
from app.models import Course, CourseSlot, Department, Instructor, QuotaSnapshot, Room, SyncState, Term
from app.sync import (
    SUBJECT_PREFIX_TO_DEPT,
    VALID_DAYS,
    _resolve_dept_for_course,
    _sanitize_shifted_payload,
    _sync_course_slots,
    _upsert_course,
    clean_int,
    ensure_department,
    ensure_instructor,
    ensure_room,
    ensure_schema_columns,
    ensure_term,
    normalize_code,
    normalize_section,
    sync_meili_documents,
    upsert_course_catalog,
    wait_meili_tasks,
)
from app.sync import (
    apply_delta_event as _apply_delta_event,
)

__all__ = [
    "DEFAULT_SCRAPER_API_URL",
    "SUBJECT_PREFIX_TO_DEPT",
    "VALID_DAYS",
    "StrictRedirectHandler",
    "ScraperClient",
    "clean_int",
    "normalize_code",
    "normalize_section",
    "ensure_term",
    "ensure_department",
    "ensure_instructor",
    "ensure_room",
    "ensure_schema_columns",
    "_sanitize_shifted_payload",
    "_sync_course_slots",
    "_upsert_course",
    "_resolve_dept_for_course",
    "_apply_delta_event",
    "_fetch_term_courses",
    "_fetch_upstream_term_runs",
    "upsert_course_catalog",
    "sync_meili_documents",
    "sync_quota_feed",
    "sync_deltas_feed",
    "backfill_term",
    "sync_terms_and_new_offerings",
    "sync_upstream_run_metadata",
    "refresh_all_data",
    "run_sync_cycle",
    "invalidate_redis_cache",
]

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("sync_from_scraper")

DEFAULT_SCRAPER_API_URL = "https://scraper.bountools.com/api/v1"


class StrictRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Prevent cross-domain, non-HTTP(S), or protocol-downgrade redirects that could leak authorization headers."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        orig_parsed = urllib.parse.urlparse(req.full_url)
        new_parsed = urllib.parse.urlparse(newurl)
        if new_parsed.scheme not in ("http", "https") or not new_parsed.netloc:
            logger.warning("Blocked unsafe redirect scheme/target: %s", newurl)
            return None
        if orig_parsed.netloc != new_parsed.netloc:
            logger.warning("Blocked cross-domain redirect from %s to %s", orig_parsed.netloc, new_parsed.netloc)
            return None
        if orig_parsed.scheme == "https" and new_parsed.scheme != "https":
            logger.warning("Blocked protocol downgrade redirect from %s to %s", orig_parsed.scheme, new_parsed.scheme)
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_RATE_LIMIT_BACKOFF_SECONDS: tuple[int, ...] = (5, 15, 35, 62)


class ScraperClient:
    def __init__(self, base_url: str | None = None, token: str | None = None, min_interval: float = 0.0):
        raw_base = (base_url or os.getenv("SCRAPER_API_URL") or DEFAULT_SCRAPER_API_URL).strip().rstrip("/")
        parsed = urllib.parse.urlsplit(raw_base)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"Invalid scraper base URL (must be http/https with host): {raw_base!r}")
        self.base_url = raw_base
        self.token = token or os.getenv("SCRAPER_FEED_TOKEN")
        self.min_interval = min_interval
        self._last_req_mono = 0.0
        self.opener = urllib.request.build_opener(StrictRedirectHandler())

    def _throttle(self) -> None:
        if self.min_interval <= 0:
            return
        elapsed = time.monotonic() - self._last_req_mono
        if self._last_req_mono > 0 and elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_req_mono = time.monotonic()

    def _build_request(self, path: str, params: dict[str, Any] | None) -> tuple[str, urllib.request.Request]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        if params:
            clean_params = {k: v for k, v in params.items() if v is not None}
            if clean_params:
                url = f"{url}?{urllib.parse.urlencode(clean_params)}"
        headers = {
            "User-Agent": "boun-archive-sync/1.0",
            "Accept": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
            headers["X-Feed-Token"] = self.token
        return url, urllib.request.Request(url, headers=headers)

    def _sleep_for_http_error(self, err: urllib.error.HTTPError, attempt: int, url: str) -> bool:
        if err.code == 429 and attempt < 3:
            raw_after = err.headers.get("Retry-After") if getattr(err, "headers", None) else None
            retry_after = clean_int(raw_after)
            delay = min(max(0, retry_after), 120) if retry_after is not None else _RATE_LIMIT_BACKOFF_SECONDS[attempt]
            logger.warning("Rate limited (429) requesting %s; retrying in %ss...", url, delay)
            time.sleep(delay)
            return True
        if err.code in (502, 503, 504) and attempt < 2:
            time.sleep(2 ** attempt)
            return True
        return False

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any | None:
        url, req = self._build_request(path, params)
        for attempt in range(4):
            self._throttle()
            try:
                with self.opener.open(req, timeout=30) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    logger.debug("Endpoint not found (404): %s", url)
                    return None
                if self._sleep_for_http_error(e, attempt, url):
                    continue
                logger.error("HTTP error %s requesting %s: %s", e.code, url, e.reason)
                raise
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                logger.error("Network error requesting %s: %s", url, e)
                raise
        return None


def _split_keyset_cursor(cursor: str | None) -> tuple[str | None, int | None]:
    """Split a persisted cursor `ts|id` (or legacy plain `ts`) into `(timestamp, after_id)`."""
    if not cursor:
        return None, None
    if "|" in cursor:
        ts_part, id_part = cursor.rsplit("|", 1)
        if id_part.isdigit():
            return ts_part, int(id_part)
    return cursor, None


def _format_keyset_cursor(ts: str | None, item_id: int | None) -> str | None:
    if not ts:
        return None
    return f"{ts}|{item_id}" if item_id is not None else ts


def _is_newer_keyset(
    ts: str | None,
    item_id: int | None,
    best_ts: str | None,
    best_id: int | None,
) -> bool:
    if not ts:
        return False
    if best_ts is None or ts > best_ts:
        return True
    return ts == best_ts and item_id is not None and (best_id is None or item_id > best_id)


def _advance_sync_cursor(
    session,
    feed_name: str,
    last_cursor: str | None,
    state: SyncState | None,
    dry_run: bool,
) -> tuple[SyncState | None, str | None]:
    """Persist updated polling cursor for incremental scraper feeds without jumping None to NOW()."""
    if dry_run or not last_cursor:
        return state, state.last_cursor if state else None
    if not state:
        state = SyncState(feed_name=feed_name, last_cursor=last_cursor)
        session.add(state)
    else:
        state.last_cursor = last_cursor
    session.commit()
    return state, last_cursor


def _parse_quota_item_fields(item: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize raw quota snapshot JSON into column-ready dict, or None if invalid."""
    term_id = item.get("term")
    course_code = normalize_code(item.get("course_code"))
    if not term_id or not course_code:
        return None
    dept_raw = item.get("department")
    if not dept_raw and course_code:
        parts = course_code.strip().split()
        if parts:
            dept_raw = parts[0]
    quota_num = clean_int(item.get("quota_numeric")) if item.get("quota_numeric") is not None else clean_int(item.get("quota"))
    current_num = clean_int(item.get("current_numeric")) if item.get("current_numeric") is not None else clean_int(item.get("current"))
    avail = clean_int(item.get("available"))
    if avail is None and quota_num is not None and current_num is not None:
        avail = max(0, quota_num - current_num)
    return {
        "term_id": term_id,
        "course_code": course_code,
        "section": normalize_section(item.get("section")),
        "department": dept_raw.strip().upper() if dept_raw else None,
        "captured_at": item.get("captured_at") or item.get("timestamp") or datetime.now(UTC).isoformat(),
        "status": item.get("status"),
        "quota": str(item.get("quota")) if item.get("quota") is not None else None,
        "current": str(item.get("current")) if item.get("current") is not None else None,
        "quota_numeric": quota_num,
        "current_numeric": current_num,
        "is_consent": bool(item.get("is_consent", False)),
        "is_unlimited": bool(item.get("is_unlimited", False)),
        "available": avail,
    }


def _upsert_quota_snapshot(session, fields: dict[str, Any], term_cache: dict[str, Term], dry_run: bool) -> str:
    """Insert or update a deduplicated QuotaSnapshot row and return its timestamp."""
    ensure_term(session, fields["term_id"], term_cache)
    existing = session.query(QuotaSnapshot).filter(
        QuotaSnapshot.term_id == fields["term_id"],
        QuotaSnapshot.course_code == fields["course_code"],
        QuotaSnapshot.section == fields["section"],
        QuotaSnapshot.department == fields["department"],
        QuotaSnapshot.captured_at == fields["captured_at"],
    ).first()
    if not existing:
        if not dry_run:
            session.add(QuotaSnapshot(**fields))
        return fields["captured_at"]
    for attr in ("status", "quota", "current", "quota_numeric", "current_numeric", "available"):
        if fields[attr] is not None:
            setattr(existing, attr, fields[attr])
    existing.is_consent = fields["is_consent"]
    existing.is_unlimited = fields["is_unlimited"]
    return fields["captured_at"]


def _build_keyset_params(cursor_ts: str | None, cursor_id: int | None, limit: int) -> dict[str, Any]:
    params: dict[str, Any] = {"limit": limit, "order": "asc"}
    if cursor_ts:
        params["after_timestamp"] = cursor_ts
    if cursor_id is not None:
        params["after_id"] = cursor_id
    return params


def _apply_quota_batch(
    session,
    data: list[dict[str, Any]],
    term_cache: dict[str, Term],
    best_ts: str | None,
    best_id: int | None,
    dry_run: bool,
) -> tuple[int, str | None, int | None]:
    synced = 0
    for item in data:
        fields = _parse_quota_item_fields(item)
        if fields is None:
            continue
        item_id = clean_int(item.get("id"))
        term_snap = dict(term_cache)
        try:
            with session.begin_nested():
                captured = _upsert_quota_snapshot(session, fields, term_cache, dry_run)
            if _is_newer_keyset(captured, item_id, best_ts, best_id):
                best_ts, best_id = captured, item_id
            synced += 1
        except Exception as e:
            term_cache.clear()
            term_cache.update(term_snap)
            logger.warning("Skipping anomalous quota snapshot item %s: %s", item.get("course_code"), e)
    return synced, best_ts, best_id


def sync_quota_feed(session, client: ScraperClient, limit: int = 500, dry_run: bool = False) -> int:
    state = session.query(SyncState).filter(SyncState.feed_name == "quota_snapshots").first()
    cursor = state.last_cursor if state else None
    term_cache: dict[str, Term] = {t.id: t for t in session.query(Term).all()}
    total_synced = 0

    while True:
        cursor_ts, cursor_id = _split_keyset_cursor(cursor)
        logger.info("Polling /feeds/quota-snapshots (cursor: %s, limit: %d)...", cursor, limit)
        try:
            data = client.get("feeds/quota-snapshots", params=_build_keyset_params(cursor_ts, cursor_id, limit))
        except Exception as e:
            logger.error("Error fetching quota snapshots: %s", e)
            break
        if not data or not isinstance(data, list):
            logger.info("No new quota snapshot records available.")
            break

        batch_synced, best_ts, best_id = _apply_quota_batch(session, data, term_cache, cursor_ts, cursor_id, dry_run)
        total_synced += batch_synced
        prev_cursor = cursor
        next_cursor = _format_keyset_cursor(best_ts, best_id)
        state, cursor = _advance_sync_cursor(session, "quota_snapshots", next_cursor, state, dry_run)
        if len(data) < limit or cursor == prev_cursor:
            break

    logger.info("Processed %d quota snapshot(s). Current cursor: %s", total_synced, cursor)
    return total_synced


def _sync_touched_meili_courses(session, meili_index: Any, touched_course_ids: set[int], dry_run: bool) -> None:
    if dry_run or not meili_index or not touched_course_ids:
        return
    ids = sorted(touched_course_ids)
    logger.info("Syncing %d delta-touched course(s) to Meilisearch...", len(ids))
    for i in range(0, len(ids), 500):
        batch_ids = ids[i : i + 500]
        courses = (
            session.query(Course)
            .options(
                joinedload(Course.term),
                joinedload(Course.department),
                joinedload(Course.instructor),
                selectinload(Course.slots).joinedload(CourseSlot.room),
            )
            .filter(Course.id.in_(batch_ids))
            .all()
        )
        sync_meili_documents(meili_index, courses)


def _index_corpus_rows(
    rows: Any,
    catalog_cache: dict[str, dict[str, Any] | None],
) -> dict[tuple[str, str | None], dict[str, Any]]:
    by_key: dict[tuple[str, str | None], dict[str, Any]] = {}
    if not isinstance(rows, list):
        return by_key
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = normalize_code(row.get("course_code"))
        if not code:
            continue
        by_key[(code, normalize_section(row.get("section")))] = row
        if code not in catalog_cache and (
            row.get("catalog_text") or row.get("catalog_en_text") or row.get("catalog_tr_text")
        ):
            catalog_cache[code] = row
    return by_key


def _load_term_corpus_lookup(
    client: ScraperClient,
    term_id: str,
    corpus_cache: dict[str, dict[tuple[str, str | None], dict[str, Any]]],
    catalog_cache: dict[str, dict[str, Any] | None],
) -> dict[tuple[str, str | None], dict[str, Any]]:
    if term_id in corpus_cache:
        return corpus_cache[term_id]
    rows = None
    try:
        rows = client.get(f"feeds/exports/{term_id.replace('/', '-')}/corpus")
    except Exception as e:
        logger.debug("Corpus lookup skipped for %s: %s", term_id, e)
    indexed = _index_corpus_rows(rows, catalog_cache)
    corpus_cache[term_id] = indexed
    return indexed


def _prepare_delta_item(
    item: dict[str, Any],
    client: ScraperClient,
    corpus_cache: dict[str, dict[tuple[str, str | None], dict[str, Any]]],
    catalog_cache: dict[str, dict[str, Any] | None],
) -> dict[str, Any]:
    ctype = str(item.get("change_type") or "").strip().lower()
    term_id = item.get("term")
    if not term_id or ctype not in ("syllabus_changed", "description_changed"):
        return item

    by_key = _load_term_corpus_lookup(client, str(term_id), corpus_cache, catalog_cache)
    if ctype != "syllabus_changed":
        return item

    new_val = item.get("new_value")
    if isinstance(new_val, dict) and new_val.get("syllabus_url") and "syllabus_text" not in new_val:
        key = (normalize_code(item.get("course_code")) or "", normalize_section(item.get("section")))
        match = by_key.get(key)
        if match and match.get("syllabus_text"):
            return {**item, "new_value": {**new_val, "syllabus_text": match["syllabus_text"]}}
    return item


def _process_delta_batch(
    session,
    client: ScraperClient,
    events: list[dict[str, Any]],
    caches: dict[str, dict[str, Any]],
    last_ts: str | None,
    last_id: int | None,
    touched_course_ids: set[int],
    deleted_course_ids: set[int],
    dry_run: bool,
    catalog_fetcher,
    corpus_cache: dict[str, dict[tuple[str, str | None], dict[str, Any]]],
    catalog_cache: dict[str, dict[str, Any] | None],
) -> tuple[int, str | None, int | None]:
    synced = 0
    sorted_events = sorted(
        events,
        key=lambda ev: (ev.get("timestamp") or ev.get("detected_at") or "", clean_int(ev.get("id")) or 0),
    )
    for item in sorted_events:
        ev_ts = item.get("timestamp") or item.get("detected_at")
        ev_id = clean_int(item.get("id"))
        prepared = _prepare_delta_item(item, client, corpus_cache, catalog_cache)
        snaps = {k: dict(v) for k, v in caches.items()}
        try:
            with session.begin_nested():
                _apply_delta_event(
                    session=session,
                    item=prepared,
                    inst_cache=caches["inst"],
                    room_cache=caches["room"],
                    dept_cache=caches["dept"],
                    term_cache=caches["term"],
                    touched_course_ids=touched_course_ids,
                    meili_index=None,
                    dry_run=dry_run,
                    catalog_fetcher=catalog_fetcher,
                    deleted_course_ids=deleted_course_ids,
                )
            synced += 1
            if _is_newer_keyset(ev_ts, ev_id, last_ts, last_id):
                last_ts, last_id = ev_ts, ev_id
        except Exception as e:
            for k, snap in snaps.items():
                caches[k].clear()
                caches[k].update(snap)
            logger.warning("Skipping anomalous delta event %s: %s", item.get("course_code"), e)
    return synced, last_ts, last_id


def _delete_meili_courses(meili_index: Any, deleted_course_ids: set[int], dry_run: bool) -> None:
    if dry_run or not meili_index or not deleted_course_ids:
        return
    delete_tasks = [meili_index.delete_document(cid) for cid in sorted(deleted_course_ids)]
    wait_meili_tasks(meili_index, delete_tasks)


def sync_deltas_feed(
    session,
    client: ScraperClient,
    meili_index=None,
    limit: int = 500,
    dry_run: bool = False,
) -> int:
    state = session.query(SyncState).filter(SyncState.feed_name == "deltas").first()
    cursor = state.last_cursor if state else None
    caches: dict[str, dict[str, Any]] = {
        "inst": {i.full_name: i.id for i in session.query(Instructor).all()},
        "room": {r.name: r.id for r in session.query(Room).all()},
        "dept": {d.kisaadi: d for d in session.query(Department).all()},
        "term": {t.id: t for t in session.query(Term).all()},
    }
    touched_course_ids: set[int] = set()
    deleted_course_ids: set[int] = set()
    corpus_cache: dict[str, dict[tuple[str, str | None], dict[str, Any]]] = {}
    catalog_cache: dict[str, dict[str, Any] | None] = {}
    total_synced = 0

    def _fetch_catalog(code: str) -> dict[str, Any] | None:
        norm = normalize_code(code) or code
        if norm in catalog_cache:
            return catalog_cache[norm]
        data = client.get(f"catalog/{urllib.parse.quote(norm, safe='')}")
        catalog_cache[norm] = data if isinstance(data, dict) else None
        return catalog_cache[norm]

    while True:
        cursor_ts, cursor_id = _split_keyset_cursor(cursor)
        logger.info("Polling /feeds/deltas (cursor: %s, limit: %d)...", cursor, limit)
        try:
            data = client.get("feeds/deltas", params=_build_keyset_params(cursor_ts, cursor_id, limit))
        except Exception as e:
            logger.error("Error fetching deltas feed: %s", e)
            break
        if not data or not isinstance(data, list):
            logger.info("No new delta events available.")
            break

        batch_synced, last_ts, last_id = _process_delta_batch(
            session=session,
            client=client,
            events=data,
            caches=caches,
            last_ts=cursor_ts,
            last_id=cursor_id,
            touched_course_ids=touched_course_ids,
            deleted_course_ids=deleted_course_ids,
            dry_run=dry_run,
            catalog_fetcher=_fetch_catalog,
            corpus_cache=corpus_cache,
            catalog_cache=catalog_cache,
        )
        total_synced += batch_synced
        prev_cursor = cursor
        next_cursor = _format_keyset_cursor(last_ts, last_id)
        state, cursor = _advance_sync_cursor(session, "deltas", next_cursor, state, dry_run)
        if len(data) < limit or cursor == prev_cursor:
            break

    _delete_meili_courses(meili_index, deleted_course_ids, dry_run)
    _sync_touched_meili_courses(session, meili_index, touched_course_ids, dry_run)
    logger.info("Processed %d delta event(s). Current cursor: %s", total_synced, cursor)
    return total_synced


def _fetch_paginated_term_courses(client: ScraperClient, term_id: str) -> list[dict[str, Any]]:
    courses_raw: list[dict[str, Any]] = []
    page = 1
    page_size = 200
    while True:
        try:
            data = client.get("courses", params={"term": term_id, "page": page, "size": page_size})
        except Exception as e:
            logger.error("Error fetching paginated courses for term %s: %s", term_id, e)
            break
        if not data or not isinstance(data, dict):
            break
        items = data.get("items") or []
        if not items:
            break
        courses_raw.extend(items)
        total = data.get("total")
        if (isinstance(total, int) and len(courses_raw) >= total) or len(items) < page_size:
            break
        page += 1
    return courses_raw


def _fetch_term_courses(client: ScraperClient, term_id: str) -> list[dict[str, Any]]:
    export_term_param = term_id.replace("/", "-")
    for variant in ("corpus", "json"):
        try:
            data = client.get(f"feeds/exports/{export_term_param}/{variant}")
            if isinstance(data, list) and (data or variant == "json"):
                return data
        except Exception as e:
            logger.debug("Export feed (%s/%s) unavailable, trying next: %s", export_term_param, variant, e)
    return _fetch_paginated_term_courses(client, term_id)


def backfill_term(
    session,
    client: ScraperClient,
    meili_index=None,
    term_id: str = "2024/2025-1",
    dry_run: bool = False
) -> int:
    logger.info("Starting backfill for term: %s", term_id)
    if not dry_run:
        ensure_term(session, term_id)

    courses_raw = _fetch_term_courses(client, term_id)
    if not courses_raw:
        logger.warning("No courses retrieved for term: %s", term_id)
        return 0

    logger.info("Retrieved %d courses for term %s. Upserting into PostgreSQL...", len(courses_raw), term_id)

    inst_cache: dict[str, int] = {i.full_name: i.id for i in session.query(Instructor).all()}
    room_cache: dict[str, int] = {r.name: r.id for r in session.query(Room).all()}
    dept_cache: dict[str, Department] = {d.kisaadi: d for d in session.query(Department).all()}
    term_cache: dict[str, Term] = {t.id: t for t in session.query(Term).all()}
    catalog_seen: set[str] = set()
    touched_courses: list[Course] = []

    for item in courses_raw:
        snap_inst = dict(inst_cache)
        snap_room = dict(room_cache)
        snap_dept = dict(dept_cache)
        snap_term = dict(term_cache)
        snap_catalog = set(catalog_seen)
        try:
            with session.begin_nested():
                dept_kisaadi = item.get("department")
                course_code = normalize_code(item.get("course_code"))
                section = normalize_section(item.get("section"))

                if not course_code:
                    continue

                course = _upsert_course(
                    session=session,
                    term_id=term_id,
                    dept_kisaadi=dept_kisaadi,
                    course_code=course_code,
                    section=section,
                    val_payload=item,
                    inst_cache=inst_cache,
                    room_cache=room_cache,
                    dept_cache=dept_cache,
                    term_cache=term_cache,
                    dry_run=dry_run,
                    catalog_seen=catalog_seen,
                )
                if course:
                    touched_courses.append(course)
        except Exception as e:
            inst_cache.clear(); inst_cache.update(snap_inst)
            room_cache.clear(); room_cache.update(snap_room)
            dept_cache.clear(); dept_cache.update(snap_dept)
            term_cache.clear(); term_cache.update(snap_term)
            catalog_seen.clear(); catalog_seen.update(snap_catalog)
            logger.warning("Skipping anomalous course %s in term %s: %s", item.get("course_code"), term_id, e)

    if not dry_run:
        session.commit()
        if meili_index and touched_courses:
            logger.info("Syncing %d backfilled course(s) to Meilisearch...", len(touched_courses))
            touched_ids = [c.id for c in touched_courses]
            for i in range(0, len(touched_ids), 500):
                batch_ids = touched_ids[i:i+500]
                updated = session.query(Course).options(
                    joinedload(Course.term),
                    joinedload(Course.department),
                    joinedload(Course.instructor),
                    selectinload(Course.slots).joinedload(CourseSlot.room)
                ).filter(Course.id.in_(batch_ids)).all()
                sync_meili_documents(meili_index, updated)

    logger.info("Backfill completed for term %s (%d courses upserted).", term_id, len(touched_courses))
    return len(touched_courses)


def _fetch_upstream_term_runs(client: ScraperClient) -> dict[str, dict[str, Any]]:
    """Fetch the latest completed scrape run per upstream term.

    Returns a {term_id: {"total": int, "started_at": str}} map derived from
    /feeds/runs, so the sync layer can detect terms that were only partially
    ingested locally (e.g. an early backfill latched onto a mid-scrape
    snapshot) and reconcile them at most once per upstream run.
    """
    runs_by_term: dict[str, dict[str, Any]] = {}
    try:
        runs = client.get("feeds/runs", params={"limit": 500})
    except Exception as e:
        logger.warning("Could not fetch upstream scrape runs for term reconciliation: %s", e)
        return runs_by_term
    if not isinstance(runs, list):
        return runs_by_term

    latest_by_term: dict[str, dict[str, Any]] = {}
    for r in runs:
        if not isinstance(r, dict):
            continue
        term_id = r.get("term")
        if not term_id or r.get("status") != "completed":
            continue
        started_at = r.get("started_at") or ""
        cur = latest_by_term.get(term_id)
        if cur is None or started_at > (cur.get("started_at") or ""):
            latest_by_term[term_id] = r

    for term_id, run in latest_by_term.items():
        total = clean_int(run.get("total_courses"))
        if total is not None and total > 0:
            runs_by_term[term_id] = {"total": total, "started_at": run.get("started_at") or ""}
    return runs_by_term


def _last_reconciled_run(session, term_id: str) -> str | None:
    state = session.query(SyncState).filter(
        SyncState.feed_name == f"term_reconciled:{term_id}"
    ).first()
    return state.last_cursor if state else None


def _mark_term_reconciled(session, term_id: str, run_started_at: str) -> None:
    feed_name = f"term_reconciled:{term_id}"
    state = session.query(SyncState).filter(SyncState.feed_name == feed_name).first()
    if not state:
        state = SyncState(feed_name=feed_name, last_cursor=run_started_at)
        session.add(state)
    else:
        state.last_cursor = run_started_at
        state.updated_at = func.now()
    session.commit()


def _reconcile_term_offerings(
    session,
    client: ScraperClient,
    meili_index: Any,
    term_id: str,
    upstream_run: dict[str, Any] | None,
    dry_run: bool,
) -> int:
    """Reconcile a single term against upstream snapshot counts or new 0-course state."""
    course_count = session.query(Course.id).filter(Course.term_id == term_id).count()
    if upstream_run is not None and course_count < upstream_run["total"]:
        if _last_reconciled_run(session, term_id) == upstream_run["started_at"]:
            logger.info(
                "Term '%s' trails upstream (%d/%d courses) but was already reconciled against run %s; skipping.",
                term_id, course_count, upstream_run["total"], upstream_run["started_at"],
            )
            return 0
        logger.info(
            "Term '%s' incomplete locally (%d/%d courses). Starting reconciliation backfill...",
            term_id, course_count, upstream_run["total"],
        )
        synced = backfill_term(session, client, meili_index=meili_index, term_id=term_id, dry_run=dry_run)
        if not dry_run and synced > 0:
            _mark_term_reconciled(session, term_id, upstream_run["started_at"])
        return synced

    if course_count == 0 and _last_reconciled_run(session, term_id) is None:
        logger.info("Found new upstream term '%s' with 0 local courses. Starting automatic backfill...", term_id)
        synced = backfill_term(session, client, meili_index=meili_index, term_id=term_id, dry_run=dry_run)
        if not dry_run:
            marker = upstream_run["started_at"] if upstream_run else "zero_upstream_offerings"
            _mark_term_reconciled(session, term_id, marker)
        return synced

    return 0


def sync_terms_and_new_offerings(
    session,
    client: ScraperClient,
    meili_index=None,
    dry_run: bool = False,
) -> int:
    """
    Discovers all available terms from upstream scraper, ensures each exists in DB,
    and backfills newly published or partially ingested terms.
    """
    logger.info("Checking upstream scraper terms for new offerings...")
    try:
        scraper_terms = client.get("terms")
        if not scraper_terms or not isinstance(scraper_terms, list):
            logger.warning("Could not retrieve terms list from scraper.")
            return 0
    except Exception as e:
        logger.warning("Failed to fetch scraper terms: %s", e)
        return 0

    upstream_runs = _fetch_upstream_term_runs(client)
    term_cache: dict[str, Term] = {t.id: t for t in session.query(Term).all()}
    total_synced_courses = 0

    for raw_term in scraper_terms:
        if not isinstance(raw_term, str) or not raw_term.strip():
            continue
        term_id = raw_term.strip()
        ensure_term(session, term_id, term_cache)
        total_synced_courses += _reconcile_term_offerings(
            session, client, meili_index, term_id, upstream_runs.get(term_id), dry_run
        )

    return total_synced_courses


def sync_upstream_run_metadata(session, client: ScraperClient, dry_run: bool = False) -> dict[str, Any] | None:
    """Fetch latest scrape run execution metadata from upstream boun-scrape."""
    try:
        runs = client.get("feeds/runs", params={"limit": 5})
        run_ts = None
        latest_run = None
        if runs and isinstance(runs, list) and len(runs) > 0:
            for r in runs:
                if isinstance(r, dict) and r.get("status") == "completed" and r.get("completed_at"):
                    latest_run = r
                    run_ts = r["completed_at"]
                    break
            if not run_ts and isinstance(runs[0], dict):
                latest_run = runs[0]
                run_ts = latest_run.get("completed_at") or latest_run.get("started_at")

        if not run_ts:
            stats = client.get("stats")
            if stats and isinstance(stats, dict) and stats.get("last_scraped"):
                run_ts = stats["last_scraped"]
                latest_run = {"status": "completed", "completed_at": run_ts}

        if run_ts and not dry_run:
            state = session.query(SyncState).filter(SyncState.feed_name == "upstream_run").first()
            if not state:
                state = SyncState(feed_name="upstream_run", last_cursor=run_ts)
                session.add(state)
            else:
                state.last_cursor = run_ts
                state.updated_at = func.now()
            session.commit()
        return latest_run
    except Exception as e:
        logger.warning("Could not fetch upstream scrape runs: %s", e)
    return None


def _try_acquire_sync_lock(session, lock_id: int = 4288192) -> bool:
    try:
        bind = session.get_bind()
        if bind and bind.dialect.name == "postgresql":
            res = session.execute(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": lock_id}).scalar()
            return bool(res)
        return True
    except Exception as e:
        logger.error("Advisory lock acquisition failed (failing closed): %s", e)
        return False


def _release_sync_lock(session, lock_id: int = 4288192) -> None:
    try:
        bind = session.get_bind()
        if bind and bind.dialect.name == "postgresql":
            session.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": lock_id})
    except Exception:
        pass


def _acquire_pinned_pg_lock(session, lock_id: int = 4288192):
    """Acquire a PostgreSQL session advisory lock on a dedicated pinned connection."""
    bind = session.get_bind()
    if not bind or bind.dialect.name != "postgresql":
        return None, True
    lock_conn = bind.connect()
    try:
        acquired = bool(
            lock_conn.execute(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": lock_id}).scalar()
        )
        if not acquired:
            lock_conn.close()
            return None, False
        return lock_conn, True
    except Exception as e:
        logger.error("Pinned advisory lock acquisition failed (failing closed): %s", e)
        lock_conn.close()
        return None, False


def _release_pinned_pg_lock(lock_conn, lock_id: int = 4288192) -> None:
    if lock_conn is None:
        return
    try:
        lock_conn.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": lock_id})
    except Exception:
        pass
    finally:
        lock_conn.close()


def _apply_db_hygiene(session, dry_run: bool) -> None:
    if dry_run:
        return
    logger.info("Applying database hygiene (cleaning bogus departments and course code spacing)...")
    try:
        session.execute(text("DELETE FROM departments WHERE kisaadi ~ '[0-9]'"))
        session.execute(
            text("UPDATE courses SET course_code = regexp_replace(trim(course_code), '\\s+', ' ', 'g') WHERE course_code LIKE '%  %'")
        )
        session.commit()
    except Exception as e:
        logger.warning("Database hygiene query notice: %s", e)
        session.rollback()


def _sync_scraper_departments(session, client: ScraperClient, dry_run: bool) -> None:
    logger.info("Fetching and syncing academic departments from scraper...")
    scraper_depts = client.get("departments")
    if not scraper_depts or not isinstance(scraper_depts, list):
        return
    dept_cache: dict[str, Department] = {d.kisaadi: d for d in session.query(Department).all()}
    for d_item in scraper_depts:
        if not isinstance(d_item, dict):
            continue
        code = (d_item.get("code") or d_item.get("kisaadi") or "").strip().upper()
        name = (d_item.get("name") or d_item.get("bolum") or "").strip()
        if code and not any(ch.isdigit() for ch in code) and code not in dept_cache:
            dept = Department(kisaadi=code, bolum=name or code)
            if not dry_run:
                session.add(dept)
            dept_cache[code] = dept
    if not dry_run:
        session.commit()
        logger.info("Departments synchronized (%d total).", len(dept_cache))


def _sync_all_terms(session, client: ScraperClient, meili_index: Any, valid_terms: list[str], dry_run: bool) -> int:
    total_upserted = 0
    total_terms_count = len(valid_terms)
    prev_interval = getattr(client, "min_interval", 0.0)
    if isinstance(client, ScraperClient) and prev_interval < 1.1:
        client.min_interval = 1.1
    try:
        for idx, term_id in enumerate(valid_terms, start=1):
            logger.info("[%d/%d] Refreshing term: %s...", idx, total_terms_count, term_id)
            try:
                count = backfill_term(session, client, meili_index=meili_index, term_id=term_id, dry_run=dry_run)
                total_upserted += count
                if not dry_run:
                    _mark_term_reconciled(session, term_id, datetime.now(UTC).isoformat())
                session.expunge_all()
            except Exception as e:
                session.rollback()
                logger.error("Error refreshing term %s: %s", term_id, e)
    finally:
        if isinstance(client, ScraperClient):
            client.min_interval = prev_interval
    return total_upserted


def refresh_all_data(
    session,
    client: ScraperClient,
    meili_index=None,
    dry_run: bool = False,
) -> int:
    """Completely refresh and standardize all academic course data from scraper."""
    logger.info("=== Starting Complete BOUN Archive Data Refresh ===")
    _apply_db_hygiene(session, dry_run)
    _sync_scraper_departments(session, client, dry_run)

    scraper_terms = client.get("terms")
    if not scraper_terms or not isinstance(scraper_terms, list):
        logger.error("Could not retrieve terms list from scraper.")
        return 0

    valid_terms = [t.strip() for t in scraper_terms if isinstance(t, str) and t.strip()]
    logger.info("Discovered %d terms to refresh from upstream scraper.", len(valid_terms))
    term_cache = {t.id: t for t in session.query(Term).all()}
    for t_id in valid_terms:
        ensure_term(session, t_id, term_cache)
    if not dry_run:
        session.commit()

    total_upserted = _sync_all_terms(session, client, meili_index, valid_terms, dry_run)
    if not dry_run:
        invalidate_redis_cache()

    logger.info("=== Complete Data Refresh Finished (%d courses upserted across %d terms) ===", total_upserted, len(valid_terms))
    return total_upserted


def run_sync_cycle(session_factory, client: ScraperClient, meili_index, args) -> None:
    session = session_factory()
    lock_conn, lock_acquired = _acquire_pinned_pg_lock(session)
    if not lock_acquired:
        logger.info("Another sync_from_scraper cycle holds the advisory lock. Skipping concurrent execution.")
        session.close()
        return

    try:
        synced_terms = 0
        synced_backfill = 0
        synced_deltas = 0
        synced_quotas = 0

        if args.mode == "refresh-all":
            synced_backfill = refresh_all_data(session, client, meili_index=meili_index, dry_run=args.dry_run)
        else:
            sync_upstream_run_metadata(session, client, dry_run=args.dry_run)

            # 1. Discover upstream terms and backfill any newly scraped semester offerings
            synced_terms = sync_terms_and_new_offerings(session, client, meili_index=meili_index, dry_run=args.dry_run)

            # 2. Run configured mode
            if args.mode == "backfill":
                synced_backfill = backfill_term(session, client, meili_index, term_id=args.term, dry_run=args.dry_run)
            elif args.mode == "full":
                synced_backfill = backfill_term(session, client, meili_index, term_id=args.term, dry_run=args.dry_run)
                synced_deltas = sync_deltas_feed(session, client, meili_index, limit=args.limit, dry_run=args.dry_run)
                synced_quotas = sync_quota_feed(session, client, limit=args.limit, dry_run=args.dry_run)
            else:
                synced_deltas = sync_deltas_feed(session, client, meili_index, limit=args.limit, dry_run=args.dry_run)
                synced_quotas = sync_quota_feed(session, client, limit=args.limit, dry_run=args.dry_run)

        total_changes = synced_terms + synced_backfill + synced_deltas + synced_quotas

        if not args.dry_run:
            now_iso = datetime.now(UTC).isoformat()
            for feed in ("local_sync", "scraper"):
                state = session.query(SyncState).filter(SyncState.feed_name == feed).first()
                if not state:
                    state = SyncState(feed_name=feed, last_cursor=now_iso)
                    session.add(state)
                else:
                    state.last_cursor = now_iso
                    state.updated_at = func.now()
            session.commit()
            if total_changes > 0:
                invalidate_redis_cache()
            else:
                logger.debug("No mutations in sync cycle; preserving Redis cache.")
    except Exception:
        session.rollback()
        raise
    finally:
        _release_pinned_pg_lock(lock_conn)
        session.close()


def invalidate_redis_cache() -> None:
    """Purge cached FastAPI response keys in Redis so updated terms/courses are immediately reflected."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379").strip()
    if not redis_url:
        return
    r = None
    try:
        import redis
        r = redis.from_url(redis_url, socket_timeout=5, socket_connect_timeout=5)
        deleted_count = 0
        batch = []
        for key in r.scan_iter(match="fastapi-cache:*", count=500):
            batch.append(key)
            if len(batch) >= 500:
                deleted_count += r.delete(*batch)
                batch = []
        if batch:
            deleted_count += r.delete(*batch)
        if deleted_count > 0:
            logger.info("Invalidated %d cached FastAPI response key(s) in Redis via SCAN.", deleted_count)
    except Exception as e:
        logger.warning("Redis cache invalidation skipped: %s", e)
    finally:
        if r is not None:
            r.close()


def _connect_meili_index(meili_url: str, meili_key: str | None) -> Any | None:
    """Create and configure the Meilisearch courses index with bounded HTTP timeout."""
    if not meili_key:
        return None
    try:
        meili_client = meilisearch.Client(meili_url, meili_key, timeout=15)
        meili_index = meili_client.index("courses")
        settings_task = meili_index.update_settings({
            'filterableAttributes': [
                'term', 'dept_code', 'department', 'instructor', 'instructor_id', 'delivery_method', 'has_syllabus'
            ],
            'searchableAttributes': [
                'course_code', 'title', 'instructor', 'department', 'catalog_text', 'syllabus_snippet'
            ],
            'faceting': {
                'maxValuesPerFacet': 10000
            },
            'pagination': {
                'maxTotalHits': 200000
            },
            'sortableAttributes': ['term', 'course_code', 'title', 'instructor', 'credits', 'ects']
        })
        wait_meili_tasks(meili_client, [settings_task], timeout_in_ms=30000)
        return meili_index
    except Exception as e:
        logger.warning("Could not connect to Meilisearch: %s. Proceeding with DB sync only.", e)
        return None


def main():
    parser = argparse.ArgumentParser(description="Ingest courses, deltas, and quota snapshots from boun-scrape")
    parser.add_argument("--mode", choices=["incremental", "backfill", "full", "refresh-all"], default="incremental",
                        help="Sync mode: incremental (default), backfill (single term), full, or refresh-all (all 146 terms)")
    parser.add_argument("--term", type=str, default="2026/2027-1", help="Target term for backfill mode")
    parser.add_argument("--limit", type=int, default=500, help="Batch limit per polling request")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run without committing database changes")
    parser.add_argument("--scraper-url", type=str, default=None, help="Base URL for scraper API")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in the background")
    parser.add_argument("--daemon-interval", type=int, default=60, help="Sleep interval in seconds for daemon mode")
    args = parser.parse_args()

    pg_url = os.getenv("DATABASE_URL")
    if not pg_url:
        logger.error("DATABASE_URL environment variable is required.")
        sys.exit(1)

    engine = create_engine(pg_url, pool_pre_ping=True)
    ensure_schema_columns(engine)

    Session = sessionmaker(bind=engine, expire_on_commit=False)
    client = ScraperClient(base_url=args.scraper_url)

    meili_url = os.getenv("MEILI_URL", "http://localhost:7700")
    meili_key = os.getenv("MEILI_MASTER_KEY")
    meili_index = _connect_meili_index(meili_url, meili_key)

    if args.daemon:
        logger.info("Starting sync_worker daemon (interval: %ds, mode: %s)...", args.daemon_interval, args.mode)
        consecutive_errors = 0
        while True:
            try:
                if meili_index is None and meili_key:
                    meili_index = _connect_meili_index(meili_url, meili_key)
                run_sync_cycle(Session, client, meili_index, args)
                consecutive_errors = 0
            except Exception as e:
                consecutive_errors += 1
                sleep_time = min(args.daemon_interval * (2 ** min(consecutive_errors - 1, 4)), 300)
                logger.warning("Transient sync cycle error (#%d): %s. Retrying in %ds...", consecutive_errors, e, sleep_time)
                time.sleep(sleep_time)
                continue

            logger.info("Daemon sleep for %d seconds...", args.daemon_interval)
            time.sleep(args.daemon_interval)
    else:
        run_sync_cycle(Session, client, meili_index, args)


if __name__ == "__main__":
    main()
