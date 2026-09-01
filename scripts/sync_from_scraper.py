import os
import sys
import json
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Set, Union
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, joinedload, selectinload
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pathutil import add_import_paths, ROOT_DIR, SCRIPT_DIR

add_import_paths()

import meilisearch
from app.database import Base
from app.models import Term, Department, Instructor, Room, Course, CourseSlot, QuotaSnapshot, CourseChange, SyncState

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("sync_from_scraper")

DEFAULT_SCRAPER_API_URL = "https://scraper.bountools.com/api/v1"


def clean_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    try:
        if isinstance(val, (int, float)):
            return int(val)
        val_str = str(val).strip()
        if not val_str:
            return None
        return int(float(val_str))
    except (ValueError, TypeError):
        return None


def normalize_code(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    return " ".join(str(code).split()).strip().upper()


def normalize_section(section: Any) -> Optional[str]:
    if section is None:
        return None
    sec_str = str(section).strip()
    return sec_str if sec_str else None


class StrictRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Prevent cross-domain redirects that could leak authorization headers."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        orig_netloc = urllib.parse.urlparse(req.full_url).netloc
        new_netloc = urllib.parse.urlparse(newurl).netloc
        if orig_netloc != new_netloc:
            logger.warning("Blocked cross-domain redirect from %s to %s", orig_netloc, new_netloc)
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class ScraperClient:
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        self.base_url = (base_url or os.getenv("SCRAPER_API_URL") or DEFAULT_SCRAPER_API_URL).rstrip("/")
        self.token = token or os.getenv("SCRAPER_FEED_TOKEN")
        self.opener = urllib.request.build_opener(StrictRedirectHandler())

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        if params:
            clean_params = {k: v for k, v in params.items() if v is not None}
            if clean_params:
                query_string = urllib.parse.urlencode(clean_params)
                url = f"{url}?{query_string}"

        headers = {
            "User-Agent": "boun-archive-sync/1.0",
            "Accept": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
            headers["X-Feed-Token"] = self.token

        req = urllib.request.Request(url, headers=headers)
        try:
            with self.opener.open(req, timeout=30) as resp:
                content = resp.read().decode("utf-8")
                return json.loads(content)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                logger.debug("Endpoint not found (404): %s", url)
                return None
            logger.error("HTTP error %s requesting %s: %s", e.code, url, e.reason)
            raise
        except Exception as e:
            logger.error("Network error requesting %s: %s", url, e)
            raise


def ensure_term(session, term_id: str, term_cache: Optional[Union[Set[str], Dict[str, Any]]] = None) -> Term:
    if term_cache is not None:
        if isinstance(term_cache, dict) and term_id in term_cache:
            cached = term_cache[term_id]
            if isinstance(cached, Term):
                return cached
        elif isinstance(term_cache, set) and term_id in term_cache:
            term_in_session = session.get(Term, term_id) if hasattr(session, "get") else None
            if term_in_session:
                return term_in_session
            return session.query(Term).filter(Term.id == term_id).first()

    term = session.query(Term).filter(Term.id == term_id).first()
    if not term:
        year = term_id
        sem = 1
        if "-" in term_id:
            parts = term_id.rsplit("-", 1)
            year = parts[0]
            sem = clean_int(parts[1]) or 1
        elif "/" in term_id:
            parts = term_id.rsplit("/", 1)
            year = parts[0]
            sem = clean_int(parts[1]) or 1
        term = Term(id=term_id, academic_year=year, semester_num=sem)
        session.add(term)
        session.flush()

    if term_cache is not None:
        if isinstance(term_cache, set):
            term_cache.add(term_id)
        elif isinstance(term_cache, dict):
            term_cache[term_id] = term
    return term


def ensure_department(
    session,
    dept_kisaadi: str,
    bolum: Optional[str] = None,
    dept_cache: Optional[Union[Dict[str, str], Dict[str, Department]]] = None
) -> Optional[Department]:
    if not dept_kisaadi:
        return None
    dept_kisaadi = str(dept_kisaadi)[:10].strip().upper()

    if dept_cache is not None and dept_kisaadi in dept_cache:
        cached = dept_cache[dept_kisaadi]
        if isinstance(cached, Department):
            if bolum and cached.bolum == dept_kisaadi and bolum != cached.bolum:
                cached.bolum = bolum
                session.flush()
            return cached
        elif isinstance(cached, str):
            dept_bolum = cached
            if bolum and dept_bolum == dept_kisaadi and bolum != dept_bolum:
                dept = session.query(Department).filter(Department.kisaadi == dept_kisaadi).first()
                if dept:
                    dept.bolum = bolum
                    dept_cache[dept_kisaadi] = bolum
                    session.flush()
                    return dept
            dept_in_session = session.get(Department, dept_kisaadi) if hasattr(session, "get") else None
            if dept_in_session:
                return dept_in_session
            dept = session.query(Department).filter(Department.kisaadi == dept_kisaadi).first()
            if dept:
                return dept

    dept = session.query(Department).filter(Department.kisaadi == dept_kisaadi).first()
    if not dept:
        dept = Department(kisaadi=dept_kisaadi, bolum=bolum or dept_kisaadi)
        session.add(dept)
        session.flush()
    elif bolum and dept.bolum == dept.kisaadi and bolum != dept.bolum:
        dept.bolum = bolum
        session.flush()

    if dept_cache is not None:
        dept_cache[dept_kisaadi] = dept
    return dept


def ensure_instructor(session, full_name: Optional[str], inst_cache: Dict[str, int]) -> Optional[int]:
    if not full_name or not full_name.strip():
        return None
    name = full_name.strip()
    if name in inst_cache:
        return inst_cache[name]

    inst = session.query(Instructor).filter(Instructor.full_name == name).first()
    if not inst:
        inst = Instructor(full_name=name)
        session.add(inst)
        session.flush()
    inst_cache[name] = inst.id
    return inst.id


def ensure_room(session, room_name: Optional[str], room_cache: Dict[str, int]) -> Optional[int]:
    if not room_name or not room_name.strip():
        return None
    name = room_name.strip()
    if name in room_cache:
        return room_cache[name]

    room = session.query(Room).filter(Room.name == name).first()
    if not room:
        room = Room(name=name)
        session.add(room)
        session.flush()
    room_cache[name] = room.id
    return room.id


def sync_meili_documents(meili_index, courses: List[Course], chunk_size: int = 1000):
    if not meili_index or not courses:
        return
    documents = []
    for c in courses:
        slots_data = []
        for s in c.slots:
            slots_data.append({
                "day_code": s.day_code,
                "slot_hour": s.slot_hour,
                "slot_title": s.slot_title,
                "room_name": s.room.name if s.room else None
            })
        doc = {
            "id": c.id,
            "course_code": c.course_code,
            "title": c.title,
            "section": c.section,
            "term": c.term_id,
            "department": c.department.bolum if c.department else None,
            "dept_code": (c.dept_kisaadi.upper() if c.dept_kisaadi else (c.course_code.split()[0].upper() if c.course_code else None)),
            "instructor": c.instructor.full_name if c.instructor else "TBA",
            "instructor_id": c.instructor_id,
            "credits": c.credits,
            "ects": c.ects,
            "delivery_method": c.delivery_method,
            "slots": slots_data
        }
        documents.append(doc)
        if len(documents) >= chunk_size:
            meili_index.add_documents(documents)
            logger.info("Pushed %d document(s) to Meilisearch index", len(documents))
            documents = []

    if documents:
        meili_index.add_documents(documents)
        logger.info("Pushed %d document(s) to Meilisearch index", len(documents))


def sync_quota_feed(session, client: ScraperClient, limit: int = 500, dry_run: bool = False) -> int:
    state = session.query(SyncState).filter(SyncState.feed_name == "quota_snapshots").first()
    cursor = state.last_cursor if state else None

    term_cache: Dict[str, Term] = {t.id: t for t in session.query(Term).all()}
    total_synced = 0

    while True:
        logger.info("Polling /feeds/quota-snapshots (cursor: %s, limit: %d)...", cursor, limit)
        params = {"limit": limit}
        if cursor:
            params["after_timestamp"] = cursor

        try:
            data = client.get("feeds/quota-snapshots", params=params)
        except Exception as e:
            logger.error("Error fetching quota snapshots: %s", e)
            break

        if not data or not isinstance(data, list):
            logger.info("No new quota snapshot records available.")
            break

        last_captured_at = cursor
        for item in data:
            term_id = item.get("term")
            course_code = normalize_code(item.get("course_code"))
            section = normalize_section(item.get("section"))
            if not term_id or not course_code:
                continue

            ensure_term(session, term_id, term_cache)

            captured = item.get("captured_at") or item.get("timestamp") or datetime.now(timezone.utc).isoformat()
            dept_raw = item.get("department")
            if not dept_raw and course_code:
                parts = course_code.strip().split()
                if parts:
                    dept_raw = parts[0]
            dept = dept_raw.strip().upper() if dept_raw else None
            status = item.get("status")
            quota_raw = str(item.get("quota")) if item.get("quota") is not None else None
            current_raw = str(item.get("current")) if item.get("current") is not None else None
            quota_num = clean_int(item.get("quota_numeric")) if item.get("quota_numeric") is not None else clean_int(item.get("quota"))
            current_num = clean_int(item.get("current_numeric")) if item.get("current_numeric") is not None else clean_int(item.get("current"))
            avail = clean_int(item.get("available"))
            if avail is None and quota_num is not None and current_num is not None:
                avail = max(0, quota_num - current_num)

            # Deduplication & idempotent upsert
            existing = session.query(QuotaSnapshot).filter(
                QuotaSnapshot.term_id == term_id,
                QuotaSnapshot.course_code == course_code,
                QuotaSnapshot.section == section,
                QuotaSnapshot.department == dept,
                QuotaSnapshot.captured_at == captured
            ).first()

            if not existing:
                snapshot = QuotaSnapshot(
                    term_id=term_id,
                    course_code=course_code,
                    section=section,
                    department=dept,
                    status=status,
                    quota=quota_raw,
                    current=current_raw,
                    quota_numeric=quota_num,
                    current_numeric=current_num,
                    is_consent=bool(item.get("is_consent", False)),
                    is_unlimited=bool(item.get("is_unlimited", False)),
                    available=avail,
                    captured_at=captured
                )
                if not dry_run:
                    session.add(snapshot)
            else:
                if status is not None:
                    existing.status = status
                if quota_raw is not None:
                    existing.quota = quota_raw
                if current_raw is not None:
                    existing.current = current_raw
                if quota_num is not None:
                    existing.quota_numeric = quota_num
                if current_num is not None:
                    existing.current_numeric = current_num
                existing.is_consent = bool(item.get("is_consent", existing.is_consent))
                existing.is_unlimited = bool(item.get("is_unlimited", existing.is_unlimited))
                if avail is not None:
                    existing.available = avail

            if captured:
                if last_captured_at is None or captured > last_captured_at:
                    last_captured_at = captured
            total_synced += 1

        if not dry_run:
            if not last_captured_at:
                last_captured_at = datetime.now(timezone.utc).isoformat()
            if not state:
                state = SyncState(feed_name="quota_snapshots", last_cursor=last_captured_at)
                session.add(state)
            else:
                state.last_cursor = last_captured_at
            session.commit()
            cursor = last_captured_at

        if len(data) < limit:
            break

    logger.info("Processed %d quota snapshot(s). Current cursor: %s", total_synced, cursor)
    return total_synced


VALID_DAYS = {"M", "T", "W", "Th", "F", "St", "Su"}


def _sanitize_shifted_payload(val_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Self-healing normalizer for upstream scraper table parsing shifts.
    Detects when table columns were shifted (e.g. instructor='Info', slots broken into character array).
    Reconstructs instructor name, slot hours, and rooms without failing ingestion.
    """
    if not isinstance(val_payload, dict):
        return val_payload

    raw_inst = (val_payload.get("instructor") or "").strip()
    raw_delivery = str(val_payload.get("delivery_method") or "").strip()
    raw_exam_date = (val_payload.get("exam_date") or "").strip()
    slots = val_payload.get("slots") or val_payload.get("course_slots") or []

    is_shifted = (
        raw_inst.lower() in ("info", "detay", "details") and
        len(slots) > 0 and
        all(len(s.get("day", s.get("day_code", ""))) == 1 for s in slots)
    )

    if not is_shifted:
        return val_payload

    p = dict(val_payload)
    # 1. Reconstruct instructor from slots day characters
    reconstructed_inst = "".join(s.get("day", s.get("day_code", "")) for s in slots if s.get("day") or s.get("day_code")).strip()
    p["instructor"] = reconstructed_inst if reconstructed_inst else "TBA"

    # 2. Reconstruct hours from delivery_method if it is purely numeric digits
    hours = []
    if raw_delivery.isdigit():
        hours = [int(ch) for ch in raw_delivery if ch.isdigit() and 1 <= int(ch) <= 14]
        p["delivery_method"] = ""

    # 3. Reconstruct rooms/days from exam_date
    rooms = [r.strip() for r in raw_exam_date.split("|") if r.strip()]
    new_slots = []
    if hours:
        for idx, hr in enumerate(hours):
            room_str = rooms[idx] if idx < len(rooms) else (rooms[0] if rooms else "")
            parts = room_str.split(None, 1)
            if parts and parts[0] in VALID_DAYS:
                day_code = parts[0]
                room_val = parts[1] if len(parts) > 1 else ""
            else:
                day_code = "M"
                room_val = room_str
            new_slots.append({
                "day": day_code,
                "hour": hr,
                "room": room_val,
                "slot_title": p.get("course_name") or p.get("title"),
                "instructor": reconstructed_inst
            })
    p["slots"] = new_slots
    return p


def _sync_course_slots(
    session,
    course_id: int,
    slots_payload: Optional[List[Dict[str, Any]]],
    room_cache: Dict[str, int],
    dry_run: bool = False
) -> None:
    if slots_payload is None or dry_run:
        return
    session.query(CourseSlot).filter(CourseSlot.course_id == course_id).delete(synchronize_session="fetch")
    for s in slots_payload:
        slot_hour = clean_int(s.get("hour") or s.get("slot_hour"))
        if slot_hour is None or slot_hour < 1 or slot_hour > 14:
            continue
        day_raw = (s.get("day") or s.get("day_code") or "").strip()
        if not day_raw:
            continue
        day_code = day_raw if day_raw in VALID_DAYS else (day_raw.capitalize() if day_raw.capitalize() in VALID_DAYS else "M")

        room_name = s.get("room") or s.get("room_name")
        room_id = ensure_room(session, room_name, room_cache)
        slot = CourseSlot(
            course_id=course_id,
            day_code=day_code,
            slot_hour=slot_hour,
            slot_title=s.get("slot_title"),
            room_id=room_id
        )
        session.add(slot)
    session.flush()


def _upsert_course(
    session,
    term_id: str,
    dept_kisaadi: Optional[str],
    course_code: str,
    section: Optional[str],
    val_payload: Dict[str, Any],
    inst_cache: Dict[str, int],
    room_cache: Dict[str, int],
    dept_cache: Optional[Union[Dict[str, str], Dict[str, Department]]],
    term_cache: Optional[Union[Set[str], Dict[str, Any]]],
    dry_run: bool = False
) -> Optional[Course]:
    val_payload = _sanitize_shifted_payload(val_payload)
    ensure_term(session, term_id, term_cache)

    if dept_kisaadi and str(dept_kisaadi).strip():
        dept_kisaadi = str(dept_kisaadi).strip().upper()
        dept = ensure_department(session, dept_kisaadi, dept_cache=dept_cache)
        if dept:
            dept_kisaadi = dept.kisaadi

    title = val_payload.get("course_name") or val_payload.get("title")
    instructor_name = val_payload.get("instructor")
    instructor_id = ensure_instructor(session, instructor_name, inst_cache)
    credits = clean_int(val_payload.get("credits"))
    ects = clean_int(val_payload.get("ects"))
    delivery_method = val_payload.get("delivery_method")

    course = session.query(Course).filter(
        Course.term_id == term_id,
        Course.course_code == course_code,
        Course.section == section
    ).first()

    if not course:
        course = Course(
            term_id=term_id,
            dept_kisaadi=dept_kisaadi,
            course_code=course_code,
            section=section,
            title=title,
            instructor_id=instructor_id,
            credits=credits,
            ects=ects,
            delivery_method=delivery_method
        )
        if not dry_run:
            session.add(course)
            session.flush()
    else:
        if dept_kisaadi is not None:
            course.dept_kisaadi = dept_kisaadi
        if title is not None:
            course.title = title
        if instructor_id is not None:
            course.instructor_id = instructor_id
        if credits is not None:
            course.credits = credits
        if ects is not None:
            course.ects = ects
        if delivery_method is not None:
            course.delivery_method = delivery_method
        if not dry_run:
            session.flush()

    slots_payload = val_payload.get("slots") or val_payload.get("course_slots")
    if course and course.id:
        _sync_course_slots(session, course.id, slots_payload, room_cache, dry_run=dry_run)

    return course


def _apply_delta_event(
    session,
    item: Dict[str, Any],
    inst_cache: Dict[str, int],
    room_cache: Dict[str, int],
    dept_cache: Optional[Union[Dict[str, str], Dict[str, Department]]],
    term_cache: Optional[Union[Set[str], Dict[str, Any]]],
    touched_course_ids: Set[int],
    meili_index,
    dry_run: bool = False
) -> None:
    raw_change_type = item.get("change_type")
    term_id = item.get("term")
    course_code = normalize_code(item.get("course_code"))
    raw_dept = item.get("department")
    if not raw_dept and course_code:
        parts = course_code.strip().split()
        if parts:
            raw_dept = parts[0]
    dept_kisaadi = raw_dept.strip().upper() if raw_dept else None
    section = normalize_section(item.get("section"))
    timestamp = item.get("timestamp") or ""

    if not raw_change_type or not term_id or not course_code:
        return

    change_type = str(raw_change_type).strip().lower()

    if not dry_run:
        change_log = CourseChange(
            change_type=raw_change_type,
            term_id=term_id,
            dept_kisaadi=dept_kisaadi,
            course_code=course_code,
            section=section,
            timestamp=timestamp,
            old_value=json.dumps(item.get("old_value")) if item.get("old_value") else None,
            new_value=json.dumps(item.get("new_value")) if item.get("new_value") else None,
            details=item.get("details")
        )
        session.add(change_log)

    if change_type in ("added", "insert", "inserted", "create", "created", "modified", "update", "updated", "modify"):
        val_payload = item.get("new_value") or {}
        if not val_payload and any(k in item for k in ("course_name", "title", "instructor", "credits", "ects", "slots", "course_slots")):
            val_payload = item
        course = _upsert_course(
            session=session,
            term_id=term_id,
            dept_kisaadi=dept_kisaadi,
            course_code=course_code,
            section=section,
            val_payload=val_payload,
            inst_cache=inst_cache,
            room_cache=room_cache,
            dept_cache=dept_cache,
            term_cache=term_cache,
            dry_run=dry_run
        )
        if course and course.id:
            touched_course_ids.add(course.id)

    elif change_type in ("removed", "delete", "deleted", "remove", "drop", "dropped"):
        course = session.query(Course).filter(
            Course.term_id == term_id,
            Course.course_code == course_code,
            Course.section == section
        ).first()

        if course and not dry_run:
            course_id = course.id
            session.query(CourseSlot).filter(CourseSlot.course_id == course_id).delete(synchronize_session="fetch")
            session.delete(course)
            session.flush()
            if meili_index:
                try:
                    meili_index.delete_document(course_id)
                except Exception as e:
                    logger.warning("Meilisearch delete error for course %s: %s", course_id, e)


def _fetch_term_courses(client: ScraperClient, term_id: str) -> List[Dict[str, Any]]:
    export_term_param = term_id.replace("/", "-")
    try:
        data = client.get(f"feeds/exports/{export_term_param}/json")
        if data and isinstance(data, list):
            return data
    except Exception as e:
        logger.debug("Export feed not available (%s), falling back to /courses: %s", export_term_param, e)

    logger.info("Export feed not available, pulling paginated /courses for term %s...", term_id)
    courses_raw = []
    page = 1
    page_size = 100
    while True:
        try:
            resp = client.get("courses", params={"term": term_id, "page": page, "size": page_size})
            if not resp and "/" in term_id:
                resp = client.get("courses", params={"term": export_term_param, "page": page, "size": page_size})
            elif not resp and "-" in term_id:
                resp = client.get("courses", params={"term": term_id.replace("-", "/"), "page": page, "size": page_size})
        except Exception as e:
            logger.error("Error pulling /courses for term %s (page %d): %s", term_id, page, e)
            break
        if not resp:
            break
        items = resp.get("items", []) if isinstance(resp, dict) else resp
        if not items:
            break
        courses_raw.extend(items)
        total = resp.get("total", len(courses_raw)) if isinstance(resp, dict) else len(courses_raw)
        if len(courses_raw) >= total or len(items) < page_size:
            break
        page += 1
    return courses_raw


def sync_deltas_feed(
    session,
    client: ScraperClient,
    meili_index=None,
    limit: int = 500,
    dry_run: bool = False
) -> int:
    state = session.query(SyncState).filter(SyncState.feed_name == "deltas").first()
    cursor = state.last_cursor if state else None

    inst_cache: Dict[str, int] = {i.full_name: i.id for i in session.query(Instructor).all()}
    room_cache: Dict[str, int] = {r.name: r.id for r in session.query(Room).all()}
    dept_cache: Dict[str, Department] = {d.kisaadi: d for d in session.query(Department).all()}
    term_cache: Dict[str, Term] = {t.id: t for t in session.query(Term).all()}

    total_synced = 0

    while True:
        logger.info("Polling /feeds/deltas (cursor: %s, limit: %d)...", cursor, limit)
        params = {"limit": limit}
        if cursor:
            params["after_timestamp"] = cursor

        try:
            data = client.get("feeds/deltas", params=params)
        except Exception as e:
            logger.error("Error fetching deltas feed: %s", e)
            break

        if not data or not isinstance(data, list):
            logger.info("No new delta change events available.")
            break

        # Sort delta events ascending by timestamp to replay state changes in causal order
        data.sort(key=lambda x: x.get("timestamp") or "")

        last_timestamp = cursor
        touched_course_ids: Set[int] = set()

        for item in data:
            ts = item.get("timestamp") or ""
            if ts and (last_timestamp is None or ts > last_timestamp):
                last_timestamp = ts

            _apply_delta_event(
                session=session,
                item=item,
                inst_cache=inst_cache,
                room_cache=room_cache,
                dept_cache=dept_cache,
                term_cache=term_cache,
                touched_course_ids=touched_course_ids,
                meili_index=meili_index,
                dry_run=dry_run
            )
            total_synced += 1

        if not dry_run:
            if not last_timestamp:
                last_timestamp = datetime.now(timezone.utc).isoformat()
            if not state:
                state = SyncState(feed_name="deltas", last_cursor=last_timestamp)
                session.add(state)
            else:
                state.last_cursor = last_timestamp
            session.commit()
            cursor = last_timestamp

            # Push batch updates to Meilisearch
            if meili_index and touched_course_ids:
                updated_courses = session.query(Course).options(
                    joinedload(Course.term),
                    joinedload(Course.department),
                    joinedload(Course.instructor),
                    selectinload(Course.slots).joinedload(CourseSlot.room)
                ).filter(Course.id.in_(touched_course_ids)).all()
                sync_meili_documents(meili_index, updated_courses)

        if len(data) < limit:
            break

    logger.info("Processed %d delta change event(s). Current cursor: %s", total_synced, cursor)
    return total_synced


def backfill_term(
    session,
    client: ScraperClient,
    meili_index=None,
    term_id: str = "2024/2025-1",
    dry_run: bool = False
) -> int:
    logger.info("Starting backfill for term: %s", term_id)
    ensure_term(session, term_id)

    courses_raw = _fetch_term_courses(client, term_id)
    if not courses_raw:
        logger.warning("No courses retrieved for term: %s", term_id)
        return 0

    logger.info("Retrieved %d courses for term %s. Upserting into PostgreSQL...", len(courses_raw), term_id)

    inst_cache: Dict[str, int] = {i.full_name: i.id for i in session.query(Instructor).all()}
    room_cache: Dict[str, int] = {r.name: r.id for r in session.query(Room).all()}
    dept_cache: Dict[str, Department] = {d.kisaadi: d for d in session.query(Department).all()}
    term_cache: Dict[str, Term] = {t.id: t for t in session.query(Term).all()}
    touched_courses: List[Course] = []

    for item in courses_raw:
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
                    dry_run=dry_run
                )
                if course:
                    touched_courses.append(course)
        except Exception as e:
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


def sync_terms_and_new_offerings(
    session,
    client: ScraperClient,
    meili_index=None,
    dry_run: bool = False
) -> int:
    """
    Discovers all available terms from upstream scraper.
    Ensures each term exists in PostgreSQL terms table.
    For any term with 0 courses in local DB (e.g. newly published semester 2026/2027-1),
    automatically triggers backfill_term to ingest courses, rooms, instructors and push to Meilisearch.
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

    term_cache: Dict[str, Term] = {t.id: t for t in session.query(Term).all()}
    total_synced_courses = 0

    for term_id in scraper_terms:
        if not isinstance(term_id, str) or not term_id.strip():
            continue
        term_id = term_id.strip()
        ensure_term(session, term_id, term_cache)

        # Check if local DB has courses for this term
        course_count = session.query(Course.id).filter(Course.term_id == term_id).count()
        if course_count == 0:
            logger.info("Found new upstream term '%s' with 0 local courses. Starting automatic backfill...", term_id)
            synced = backfill_term(session, client, meili_index=meili_index, term_id=term_id, dry_run=dry_run)
            total_synced_courses += synced

    return total_synced_courses


def sync_upstream_run_metadata(session, client: ScraperClient, dry_run: bool = False) -> Optional[Dict[str, Any]]:
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


def run_sync_cycle(session_factory, client: ScraperClient, meili_index, args) -> None:
    session = session_factory()
    try:
        sync_upstream_run_metadata(session, client, dry_run=args.dry_run)

        # 1. Discover upstream terms and backfill any newly scraped semester offerings
        sync_terms_and_new_offerings(session, client, meili_index=meili_index, dry_run=args.dry_run)

        # 2. Run configured mode
        if args.mode == "backfill":
            backfill_term(session, client, meili_index, term_id=args.term, dry_run=args.dry_run)
        elif args.mode == "full":
            backfill_term(session, client, meili_index, term_id=args.term, dry_run=args.dry_run)
            sync_deltas_feed(session, client, meili_index, limit=args.limit, dry_run=args.dry_run)
            sync_quota_feed(session, client, limit=args.limit, dry_run=args.dry_run)
        else:
            sync_deltas_feed(session, client, meili_index, limit=args.limit, dry_run=args.dry_run)
            sync_quota_feed(session, client, limit=args.limit, dry_run=args.dry_run)

        if not args.dry_run:
            now_iso = datetime.now(timezone.utc).isoformat()
            for feed in ("local_sync", "scraper"):
                state = session.query(SyncState).filter(SyncState.feed_name == feed).first()
                if not state:
                    state = SyncState(feed_name=feed, last_cursor=now_iso)
                    session.add(state)
                else:
                    state.last_cursor = now_iso
                    state.updated_at = func.now()
            session.commit()
            invalidate_redis_cache()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def invalidate_redis_cache() -> None:
    """Purge cached FastAPI response keys in Redis so updated terms/courses are immediately reflected."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return
    try:
        import redis
        r = redis.from_url(redis_url)
        keys = r.keys("fastapi-cache:*")
        if keys:
            r.delete(*keys)
            logger.info("Invalidated %d cached FastAPI response key(s) in Redis.", len(keys))
    except Exception as e:
        logger.debug("Redis cache invalidation skipped: %s", e)


def main():
    parser = argparse.ArgumentParser(description="Ingest courses, deltas, and quota snapshots from boun-scrape")
    parser.add_argument("--mode", choices=["incremental", "backfill", "full"], default="incremental",
                        help="Sync mode: incremental (default), backfill (single term), or full")
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
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine, expire_on_commit=False)
    client = ScraperClient(base_url=args.scraper_url)

    meili_index = None
    meili_url = os.getenv("MEILI_URL", "http://localhost:7700")
    meili_key = os.getenv("MEILI_MASTER_KEY")
    if meili_key:
        try:
            meili_client = meilisearch.Client(meili_url, meili_key)
            meili_index = meili_client.index("courses")
            meili_index.update_settings({
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
        except Exception as e:
            logger.warning("Could not connect to Meilisearch: %s. Proceeding with DB sync only.", e)

    if args.daemon:
        logger.info("Starting sync_worker daemon (interval: %ds, mode: %s)...", args.daemon_interval, args.mode)
        consecutive_errors = 0
        while True:
            try:
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
