"""Core synchronization and webhook ingestion utilities for boun-archive.

Provides shared domain parsing, idempotent database upserts, Meilisearch
document formatting, and HMAC-SHA256 signature verification used by both the
REST webhook endpoints and the background ingestion daemon.
"""

import hmac
import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union

from sqlalchemy.orm import Session, joinedload, selectinload
from . import models

logger = logging.getLogger(__name__)

VALID_DAYS = {"M", "T", "W", "Th", "F", "St", "Su"}


def clean_int(val: Any) -> Optional[int]:
    """Cleanly parse integer values, handling None and floats."""
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
    """Normalize course codes to standard single-spaced uppercase strings."""
    if not code:
        return None
    return " ".join(str(code).split()).strip().upper()


def normalize_section(section: Any) -> Optional[str]:
    """Normalize section tokens, preserving two-character strings."""
    if section is None:
        return None
    sec_str = str(section).strip()
    return sec_str if sec_str else None


def verify_webhook_signature(raw_body: bytes, signature: Optional[str], secret: Optional[str]) -> bool:
    """Verify HMAC-SHA256 signature from boun-scrape WebhookDispatcher.

    Returns True if:
      - secret is None or empty (signature check disabled for local development)
      - signature matches the computed HMAC-SHA256 hex digest using constant-time comparison
    """
    if not secret or not secret.strip():
        return True
    if not signature:
        return False
    computed = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    # Support optional 'sha256=' prefix if provided
    clean_sig = signature.removeprefix("sha256=").strip()
    return hmac.compare_digest(computed.lower(), clean_sig.lower())


def ensure_term(session: Session, term_id: str, term_cache: Optional[Dict[str, models.Term]] = None) -> models.Term:
    """Ensure academic term exists in database."""
    if term_cache is not None and term_id in term_cache:
        return term_cache[term_id]

    term = session.query(models.Term).filter(models.Term.id == term_id).first()
    if not term:
        parts = term_id.rsplit('-', 1) if '-' in term_id else term_id.rsplit('/', 1)
        year = parts[0]
        sem = clean_int(parts[1]) if len(parts) > 1 else 1
        term = models.Term(id=term_id, academic_year=year, semester_num=sem or 1)
        session.add(term)
        session.flush()

    if term_cache is not None:
        term_cache[term_id] = term
    return term


def ensure_department(
    session: Session,
    dept_kisaadi: str,
    bolum: Optional[str] = None,
    dept_cache: Optional[Dict[str, models.Department]] = None
) -> Optional[models.Department]:
    """Ensure academic department exists, rejecting invalid numeric codes."""
    if not dept_kisaadi or not dept_kisaadi.strip():
        return None
    clean_kisaadi = dept_kisaadi.strip().upper()
    if any(ch.isdigit() for ch in clean_kisaadi):
        return None

    if dept_cache is not None and clean_kisaadi in dept_cache:
        return dept_cache[clean_kisaadi]

    dept = session.query(models.Department).filter(models.Department.kisaadi == clean_kisaadi).first()
    if not dept:
        dept = models.Department(kisaadi=clean_kisaadi, bolum=bolum or clean_kisaadi)
        session.add(dept)
        session.flush()

    if dept_cache is not None:
        dept_cache[clean_kisaadi] = dept
    return dept


def ensure_instructor(
    session: Session,
    full_name: Optional[str],
    inst_cache: Optional[Dict[str, int]] = None
) -> Optional[int]:
    """Ensure instructor exists and return instructor ID."""
    if not full_name or not full_name.strip() or full_name.strip().upper() in ("STAFF", "TBA", "OFFERED", "NONE"):
        return None
    name = full_name.strip()
    if inst_cache is not None and name in inst_cache:
        return inst_cache[name]

    inst = session.query(models.Instructor).filter(models.Instructor.full_name == name).first()
    if not inst:
        inst = models.Instructor(full_name=name)
        session.add(inst)
        session.flush()

    if inst_cache is not None:
        inst_cache[name] = inst.id
    return inst.id


def ensure_room(
    session: Session,
    room_name: Optional[str],
    room_cache: Optional[Dict[str, int]] = None
) -> Optional[int]:
    """Ensure classroom exists and return room ID."""
    if not room_name or not room_name.strip() or room_name.strip().upper() in ("TBA", "N/A", "NONE"):
        return None
    name = room_name.strip()
    if room_cache is not None and name in room_cache:
        return room_cache[name]

    room = session.query(models.Room).filter(models.Room.name == name).first()
    if not room:
        room = models.Room(name=name)
        session.add(room)
        session.flush()

    if room_cache is not None:
        room_cache[name] = room.id
    return room.id


def _sync_course_slots(
    session: Session,
    course_id: int,
    slots_payload: Optional[List[Dict[str, Any]]],
    room_cache: Dict[str, int],
    dry_run: bool = False
) -> None:
    """Sync course slots, forward-filling rooms across contiguous hours."""
    if slots_payload is None or dry_run:
        return

    session.query(models.CourseSlot).filter(models.CourseSlot.course_id == course_id).delete(synchronize_session="fetch")

    parsed_slots: List[Dict[str, Any]] = []
    for s in slots_payload:
        slot_hour = clean_int(s.get("hour") or s.get("slot_hour"))
        if slot_hour is None or slot_hour < 1 or slot_hour > 14:
            continue
        day_raw = (s.get("day") or s.get("day_code") or "").strip()
        if not day_raw:
            continue
        day_code = day_raw if day_raw in VALID_DAYS else (day_raw.capitalize() if day_raw.capitalize() in VALID_DAYS else "M")
        room_name = (s.get("room") or s.get("room_name") or "").strip()
        parsed_slots.append({
            "day_code": day_code,
            "slot_hour": slot_hour,
            "slot_title": s.get("slot_title"),
            "room_name": room_name if room_name and room_name != "N/A" else None
        })

    # Forward-fill contiguous hours within the same session/day
    day_groups: Dict[str, List[Dict[str, Any]]] = {}
    for ps in parsed_slots:
        day_groups.setdefault(ps["day_code"], []).append(ps)

    for day_code, day_slots in day_groups.items():
        day_slots.sort(key=lambda x: x["slot_hour"])
        curr_room = None
        curr_hour = None
        for ps in day_slots:
            hr = ps["slot_hour"]
            r_name = ps["room_name"]
            if not r_name and curr_room and curr_hour is not None and hr == curr_hour + 1:
                r_name = curr_room
                ps["room_name"] = curr_room
            elif r_name:
                curr_room = r_name
            else:
                curr_room = None
            curr_hour = hr

            room_id = ensure_room(session, ps["room_name"], room_cache) if ps["room_name"] else None
            slot = models.CourseSlot(
                course_id=course_id,
                day_code=ps["day_code"],
                slot_hour=ps["slot_hour"],
                slot_title=ps["slot_title"],
                room_id=room_id
            )
            session.add(slot)

    session.flush()


def _upsert_course(
    session: Session,
    term_id: str,
    dept_kisaadi: Optional[str],
    course_code: str,
    section: Optional[str],
    val_payload: Dict[str, Any],
    inst_cache: Dict[str, int],
    room_cache: Dict[str, int],
    dept_cache: Optional[Dict[str, models.Department]] = None,
    term_cache: Optional[Dict[str, models.Term]] = None,
    dry_run: bool = False
) -> Optional[models.Course]:
    """Upsert course and its corresponding session slots."""
    ensure_term(session, term_id, term_cache)

    if dept_kisaadi and str(dept_kisaadi).strip():
        dept_kisaadi = str(dept_kisaadi).strip().upper()
        dept = ensure_department(session, dept_kisaadi, dept_cache=dept_cache)
        if dept:
            dept_kisaadi = dept.kisaadi
        else:
            dept_kisaadi = None

    title = val_payload.get("course_name") or val_payload.get("title")
    instructor_name = val_payload.get("instructor")
    instructor_id = ensure_instructor(session, instructor_name, inst_cache)
    credits = clean_int(val_payload.get("credits"))
    ects = clean_int(val_payload.get("ects"))
    delivery_method = val_payload.get("delivery_method")

    course = session.query(models.Course).filter(
        models.Course.term_id == term_id,
        models.Course.course_code == course_code,
        models.Course.section == section
    ).first()

    if not course:
        course = models.Course(
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


def apply_delta_event(
    session: Session,
    item: Dict[str, Any],
    inst_cache: Optional[Dict[str, int]] = None,
    room_cache: Optional[Dict[str, int]] = None,
    dept_cache: Optional[Dict[str, models.Department]] = None,
    term_cache: Optional[Dict[str, models.Term]] = None,
    touched_course_ids: Optional[Set[int]] = None,
    meili_index = None,
    dry_run: bool = False
) -> Optional[int]:
    """Apply a discrete course delta event to PostgreSQL."""
    raw_change_type = item.get("change_type")
    term_id = item.get("term")
    course_code = normalize_code(item.get("course_code"))
    raw_dept = item.get("department")

    if not raw_dept and course_code:
        match = re.match(r"^([A-Za-z]+)", course_code.strip())
        if match:
            raw_dept = match.group(1)

    dept_kisaadi = raw_dept.strip().upper() if raw_dept else None
    if dept_kisaadi and any(c.isdigit() for c in dept_kisaadi):
        dept_kisaadi = None

    section = normalize_section(item.get("section"))
    timestamp = item.get("timestamp") or datetime.now(timezone.utc).isoformat()

    if not raw_change_type or not term_id or not course_code:
        return None

    if inst_cache is None:
        inst_cache = {i.full_name: i.id for i in session.query(models.Instructor).all()}
    if room_cache is None:
        room_cache = {r.name: r.id for r in session.query(models.Room).all()}
    if dept_cache is None:
        dept_cache = {d.kisaadi: d for d in session.query(models.Department).all()}
    if term_cache is None:
        term_cache = {t.id: t for t in session.query(models.Term).all()}

    change_type = str(raw_change_type).strip().lower()

    if not dry_run:
        change_log = models.CourseChange(
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

    touched_id: Optional[int] = None

    if change_type in ("added", "insert", "inserted", "create", "created", "modified", "update", "updated", "modify", "room_changed", "slots_changed", "instructor_changed"):
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
            touched_id = course.id
            if touched_course_ids is not None:
                touched_course_ids.add(course.id)

    elif change_type in ("removed", "delete", "deleted", "remove", "drop", "dropped"):
        course = session.query(models.Course).filter(
            models.Course.term_id == term_id,
            models.Course.course_code == course_code,
            models.Course.section == section
        ).first()

        if course and not dry_run:
            course_id = course.id
            session.query(models.CourseSlot).filter(models.CourseSlot.course_id == course_id).delete(synchronize_session="fetch")
            session.delete(course)
            session.flush()
            if meili_index:
                try:
                    meili_index.delete_document(course_id)
                except Exception as e:
                    logger.warning("Meilisearch delete error for course %s: %s", course_id, e)

    return touched_id


def sync_meili_documents(meili_index, courses: List[models.Course], chunk_size: int = 1000):
    """Serialize courses to Meilisearch search documents and push in batches."""
    if not meili_index or not courses:
        return
    documents = []
    for c in courses:
        slots_data = []
        for s in c.slots:
            r_name = s.room.name if s.room else None
            slots_data.append({
                "day_code": s.day_code,
                "slot_hour": s.slot_hour,
                "slot_title": s.slot_title,
                "room": r_name,
                "room_name": r_name
            })

        doc = {
            "id": c.id,
            "term": c.term_id,
            "course_code": c.course_code,
            "section": c.section or "01",
            "title": c.title or "",
            "dept_code": c.dept_kisaadi,
            "department": c.department.bolum if c.department else c.dept_kisaadi,
            "instructor": c.instructor.full_name if c.instructor else "TBA",
            "instructor_id": c.instructor_id,
            "credits": c.credits,
            "ects": c.ects,
            "delivery_method": c.delivery_method or "",
            "slots": slots_data
        }
        documents.append(doc)

    for i in range(0, len(documents), chunk_size):
        chunk = documents[i:i + chunk_size]
        try:
            meili_index.add_documents(chunk)
            logger.info("Pushed %d document(s) to Meilisearch index", len(chunk))
        except Exception as e:
            logger.error("Failed pushing %d documents to Meilisearch: %s", len(chunk), e)


def apply_deltas_batch(
    session: Session,
    deltas: List[Dict[str, Any]],
    meili_index = None,
    dry_run: bool = False
) -> List[int]:
    """Apply a batch of delta events in a single transaction."""
    touched_ids: Set[int] = set()
    inst_cache = {i.full_name: i.id for i in session.query(models.Instructor).all()}
    room_cache = {r.name: r.id for r in session.query(models.Room).all()}
    dept_cache = {d.kisaadi: d for d in session.query(models.Department).all()}
    term_cache = {t.id: t for t in session.query(models.Term).all()}

    for item in deltas:
        try:
            apply_delta_event(
                session=session,
                item=item,
                inst_cache=inst_cache,
                room_cache=room_cache,
                dept_cache=dept_cache,
                term_cache=term_cache,
                touched_course_ids=touched_ids,
                meili_index=meili_index,
                dry_run=dry_run
            )
        except Exception as e:
            logger.warning("Error applying delta item %s: %s", item, e)

    if not dry_run:
        session.commit()
        if meili_index and touched_ids:
            updated_courses = session.query(models.Course).options(
                joinedload(models.Course.term),
                joinedload(models.Course.department),
                joinedload(models.Course.instructor),
                selectinload(models.Course.slots).joinedload(models.CourseSlot.room)
            ).filter(models.Course.id.in_(touched_ids)).all()
            sync_meili_documents(meili_index, updated_courses)

    return list(touched_ids)


def record_scrape_summary(session: Session, summary: Dict[str, Any], dry_run: bool = False) -> None:
    """Record an upstream scrape completion summary."""
    run_id = summary.get("run_id")
    term = summary.get("term")
    completed_at = summary.get("completed_at") or datetime.now(timezone.utc).isoformat()
    if not dry_run:
        if run_id:
            feed_key = f"upstream_run:{run_id}"
            state = session.query(models.SyncState).filter(models.SyncState.feed_name == feed_key).first()
            if not state:
                state = models.SyncState(feed_name=feed_key, last_cursor=completed_at)
                session.add(state)
            else:
                state.last_cursor = completed_at
        if term:
            term_key = f"term_reconciled:{term}"
            state = session.query(models.SyncState).filter(models.SyncState.feed_name == term_key).first()
            if not state:
                state = models.SyncState(feed_name=term_key, last_cursor=completed_at)
                session.add(state)
            else:
                state.last_cursor = completed_at
        session.commit()
