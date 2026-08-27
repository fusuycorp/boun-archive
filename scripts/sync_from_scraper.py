import os
import sys
import json
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error
import logging
from typing import Optional, Dict, Any, List, Set
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


def ensure_term(session, term_id: str, term_cache: Optional[Set[str]] = None) -> Term:
    if term_cache is not None and term_id in term_cache:
        return session.query(Term).filter(Term.id == term_id).first()

    term = session.query(Term).filter(Term.id == term_id).first()
    if not term:
        year = term_id
        sem = 1
        if "-" in term_id:
            parts = term_id.split("-")
            year = parts[0]
            sem = clean_int(parts[1]) or 1
        term = Term(id=term_id, academic_year=year, semester_num=sem)
        session.add(term)
        session.flush()

    if term_cache is not None:
        term_cache.add(term_id)
    return term


def ensure_department(session, dept_kisaadi: str, bolum: Optional[str] = None, dept_cache: Optional[Dict[str, str]] = None) -> Department:
    if dept_cache is not None and dept_kisaadi in dept_cache:
        dept_bolum = dept_cache[dept_kisaadi]
        if bolum and dept_bolum == dept_kisaadi and bolum != dept_bolum:
            dept = session.query(Department).filter(Department.kisaadi == dept_kisaadi).first()
            if dept:
                dept.bolum = bolum
                dept_cache[dept_kisaadi] = bolum
                session.flush()
                return dept
        return session.query(Department).filter(Department.kisaadi == dept_kisaadi).first()

    dept = session.query(Department).filter(Department.kisaadi == dept_kisaadi).first()
    if not dept:
        dept = Department(kisaadi=dept_kisaadi, bolum=bolum or dept_kisaadi)
        session.add(dept)
        session.flush()
    elif bolum and dept.bolum == dept.kisaadi and bolum != dept.bolum:
        dept.bolum = bolum
        session.flush()

    if dept_cache is not None:
        dept_cache[dept_kisaadi] = dept.bolum
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


def sync_meili_documents(meili_index, courses: List[Course]):
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
            "dept_code": c.dept_kisaadi,
            "instructor": c.instructor.full_name if c.instructor else "TBA",
            "credits": c.credits,
            "ects": c.ects,
            "delivery_method": c.delivery_method,
            "slots": slots_data
        }
        documents.append(doc)

    if documents:
        meili_index.add_documents(documents)
        logger.info("Pushed %d document(s) to Meilisearch index", len(documents))


def sync_quota_feed(session, client: ScraperClient, limit: int = 500, dry_run: bool = False) -> int:
    state = session.query(SyncState).filter(SyncState.feed_name == "quota_snapshots").first()
    cursor = state.last_cursor if state else None

    term_cache: Set[str] = {t.id for t in session.query(Term.id).all()}
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

        last_captured_at = None
        for item in data:
            term_id = item.get("term")
            course_code = normalize_code(item.get("course_code"))
            section = normalize_section(item.get("section"))
            if not term_id or not course_code:
                continue

            ensure_term(session, term_id, term_cache)

            captured = item.get("captured_at") or item.get("timestamp") or ""
            snapshot = QuotaSnapshot(
                term_id=term_id,
                course_code=course_code,
                section=section,
                department=item.get("department"),
                status=item.get("status"),
                quota=str(item.get("quota")) if item.get("quota") is not None else None,
                current=str(item.get("current")) if item.get("current") is not None else None,
                quota_numeric=clean_int(item.get("quota_numeric")),
                current_numeric=clean_int(item.get("current_numeric")),
                is_consent=bool(item.get("is_consent", False)),
                is_unlimited=bool(item.get("is_unlimited", False)),
                available=clean_int(item.get("available")),
                captured_at=captured
            )
            if not dry_run:
                session.add(snapshot)

            if captured:
                last_captured_at = captured
            total_synced += 1

        if not dry_run and last_captured_at:
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
    dept_cache: Dict[str, str] = {d.kisaadi: d.bolum for d in session.query(Department).all()}
    term_cache: Set[str] = {t.id for t in session.query(Term.id).all()}

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

        # Sort delta events ascending by timestamp to replay state changes in correct chronological order
        data.sort(key=lambda x: x.get("timestamp") or "")

        last_timestamp = cursor
        touched_course_ids = set()

        for item in data:
            change_type = item.get("change_type")
            term_id = item.get("term")
            dept_kisaadi = item.get("department")
            course_code = normalize_code(item.get("course_code"))
            section = normalize_section(item.get("section"))
            timestamp = item.get("timestamp") or ""
            old_val = item.get("old_value")
            new_val = item.get("new_value")
            details = item.get("details")

            if not change_type or not term_id or not course_code:
                continue

            if timestamp and (last_timestamp is None or timestamp > last_timestamp):
                last_timestamp = timestamp

            # Record course change history log
            if not dry_run:
                change_log = CourseChange(
                    change_type=change_type,
                    term_id=term_id,
                    dept_kisaadi=dept_kisaadi,
                    course_code=course_code,
                    section=section,
                    timestamp=timestamp,
                    old_value=json.dumps(old_val) if old_val else None,
                    new_value=json.dumps(new_val) if new_val else None,
                    details=details
                )
                session.add(change_log)

            # Look up course by natural key
            course_q = session.query(Course).filter(
                Course.term_id == term_id,
                Course.course_code == course_code,
                Course.section == section
            )
            if dept_kisaadi:
                course_q = course_q.filter(Course.dept_kisaadi == dept_kisaadi)
            course = course_q.first()

            if change_type in ("added", "modified"):
                val_payload = new_val or {}
                course_title = val_payload.get("course_name") or val_payload.get("title")
                instructor_name = val_payload.get("instructor")
                credits = clean_int(val_payload.get("credits"))
                ects = clean_int(val_payload.get("ects"))
                delivery_method = val_payload.get("delivery_method")

                ensure_term(session, term_id, term_cache)
                if dept_kisaadi:
                    ensure_department(session, dept_kisaadi, dept_cache=dept_cache)

                instructor_id = ensure_instructor(session, instructor_name, inst_cache)

                if not course:
                    course = Course(
                        term_id=term_id,
                        dept_kisaadi=dept_kisaadi,
                        course_code=course_code,
                        section=section,
                        title=course_title,
                        instructor_id=instructor_id,
                        credits=credits,
                        ects=ects,
                        delivery_method=delivery_method
                    )
                    if not dry_run:
                        session.add(course)
                        session.flush()
                else:
                    if course_title is not None:
                        course.title = course_title
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

                # Handle slots
                slots_payload = val_payload.get("slots") or val_payload.get("course_slots")
                if slots_payload is not None and not dry_run:
                    session.query(CourseSlot).filter(CourseSlot.course_id == course.id).delete()
                    for s in slots_payload:
                        room_id = ensure_room(session, s.get("room"), room_cache)
                        slot = CourseSlot(
                            course_id=course.id,
                            day_code=s.get("day") or s.get("day_code"),
                            slot_hour=clean_int(s.get("hour") or s.get("slot_hour")),
                            slot_title=s.get("slot_title"),
                            room_id=room_id
                        )
                        session.add(slot)
                    session.flush()

                if course and course.id:
                    touched_course_ids.add(course.id)

            elif change_type == "removed" and course:
                course_id = course.id
                if not dry_run:
                    session.query(CourseSlot).filter(CourseSlot.course_id == course_id).delete()
                    session.delete(course)
                    session.flush()
                    if meili_index:
                        try:
                            meili_index.delete_document(course_id)
                        except Exception as e:
                            logger.warning("Meilisearch delete error for course %s: %s", course_id, e)

            total_synced += 1

        if not dry_run and last_timestamp:
            if not state:
                state = SyncState(feed_name="deltas", last_cursor=last_timestamp)
                session.add(state)
            else:
                state.last_cursor = last_timestamp
            session.commit()
            cursor = last_timestamp

            # Update Meilisearch for modified courses
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

    export_term_param = term_id.replace("/", "-")
    data = client.get(f"feeds/exports/{export_term_param}/json")

    courses_raw = []
    if data and isinstance(data, list):
        courses_raw = data
    else:
        logger.info("Export feed not available, pulling paginated /courses for term %s...", term_id)
        page = 1
        page_size = 100
        while True:
            resp = client.get("courses", params={"term": term_id, "page": page, "size": page_size})
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

    if not courses_raw:
        logger.warning("No courses retrieved for term: %s", term_id)
        return 0

    logger.info("Retrieved %d courses for term %s. Upserting into PostgreSQL...", len(courses_raw), term_id)

    inst_cache: Dict[str, int] = {i.full_name: i.id for i in session.query(Instructor).all()}
    room_cache: Dict[str, int] = {r.name: r.id for r in session.query(Room).all()}
    dept_cache: Dict[str, str] = {d.kisaadi: d.bolum for d in session.query(Department).all()}
    touched_courses = []

    for item in courses_raw:
        dept_kisaadi = item.get("department")
        course_code = normalize_code(item.get("course_code"))
        section = normalize_section(item.get("section"))
        title = item.get("course_name") or item.get("title")
        instructor_name = item.get("instructor")
        credits = clean_int(item.get("credits"))
        ects = clean_int(item.get("ects"))
        delivery_method = item.get("delivery_method")

        if not course_code:
            continue

        if dept_kisaadi:
            ensure_department(session, dept_kisaadi, dept_cache=dept_cache)

        instructor_id = ensure_instructor(session, instructor_name, inst_cache)

        course_q = session.query(Course).filter(
            Course.term_id == term_id,
            Course.course_code == course_code,
            Course.section == section
        )
        if dept_kisaadi:
            course_q = course_q.filter(Course.dept_kisaadi == dept_kisaadi)
        course = course_q.first()

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
            course.title = title
            course.instructor_id = instructor_id
            course.credits = credits
            course.ects = ects
            course.delivery_method = delivery_method
            if not dry_run:
                session.flush()

        slots_payload = item.get("slots") or item.get("course_slots")
        if slots_payload is not None and not dry_run:
            session.query(CourseSlot).filter(CourseSlot.course_id == course.id).delete()
            for s in slots_payload:
                room_id = ensure_room(session, s.get("room"), room_cache)
                slot = CourseSlot(
                    course_id=course.id,
                    day_code=s.get("day") or s.get("day_code"),
                    slot_hour=clean_int(s.get("hour") or s.get("slot_hour")),
                    slot_title=s.get("slot_title"),
                    room_id=room_id
                )
                session.add(slot)
            session.flush()

        touched_courses.append(course)

    if not dry_run:
        session.commit()
        if meili_index and touched_courses:
            logger.info("Syncing %d backfilled course(s) to Meilisearch...", len(touched_courses))
            updated = session.query(Course).options(
                joinedload(Course.term),
                joinedload(Course.department),
                joinedload(Course.instructor),
                selectinload(Course.slots).joinedload(CourseSlot.room)
            ).filter(Course.id.in_([c.id for c in touched_courses])).all()
            sync_meili_documents(meili_index, updated)

    logger.info("Backfill completed for term %s (%d courses upserted).", term_id, len(touched_courses))
    return len(touched_courses)


def run_sync_cycle(session_factory, client: ScraperClient, meili_index, args) -> None:
    session = session_factory()
    try:
        if args.mode == "backfill":
            backfill_term(session, client, meili_index, term_id=args.term, dry_run=args.dry_run)
        elif args.mode == "full":
            backfill_term(session, client, meili_index, term_id=args.term, dry_run=args.dry_run)
            sync_deltas_feed(session, client, meili_index, limit=args.limit, dry_run=args.dry_run)
            sync_quota_feed(session, client, limit=args.limit, dry_run=args.dry_run)
        else:
            sync_deltas_feed(session, client, meili_index, limit=args.limit, dry_run=args.dry_run)
            sync_quota_feed(session, client, limit=args.limit, dry_run=args.dry_run)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="Ingest courses, deltas, and quota snapshots from boun-scrape")
    parser.add_argument("--mode", choices=["incremental", "backfill", "full"], default="incremental",
                        help="Sync mode: incremental (default), backfill (single term), or full")
    parser.add_argument("--term", type=str, default="2024/2025-1", help="Target term for backfill mode")
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
