"""Core synchronization and webhook ingestion utilities for boun-archive.

Provides shared domain parsing, idempotent database upserts, Meilisearch
document formatting, and HMAC-SHA256 signature verification used by both the
REST webhook endpoints and the background ingestion daemon.
"""

import hashlib
import hmac
import json
import logging
import os
import re
import urllib.parse
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload, object_session, selectinload

from . import models

logger = logging.getLogger(__name__)

VALID_DAYS = {"M", "T", "W", "Th", "F", "St", "Su"}


def clean_int(val: Any) -> int | None:
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


def normalize_code(code: str | None) -> str | None:
    """Normalize course codes to standard single-spaced uppercase strings."""
    if not code:
        return None
    return " ".join(str(code).split()).strip().upper()


def normalize_section(section: Any) -> str | None:
    """Normalize section tokens, preserving two-character strings."""
    if section is None:
        return None
    sec_str = str(section).strip()
    return sec_str if sec_str else None


def verify_webhook_signature(raw_body: bytes, signature: str | None, secret: str | None) -> bool:
    """Verify HMAC-SHA256 signature from boun-scrape WebhookDispatcher.

    Fails closed by default when `secret` is unset unless `ALLOW_INSECURE_WEBHOOK=1`
    is explicitly set for local development/testing.
    """
    if not secret or not secret.strip():
        return os.getenv("ALLOW_INSECURE_WEBHOOK", "").strip().lower() in ("1", "true", "yes")
    if not signature:
        return False
    computed = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    clean_sig = signature.removeprefix("sha256=").strip()
    return hmac.compare_digest(computed.lower(), clean_sig.lower())


def _parse_term_parts(term_id: str) -> tuple[str, int]:
    """Split a term identifier into `(academic_year, semester_num)`."""
    if "-" in term_id:
        parts = term_id.rsplit("-", 1)
        return parts[0], clean_int(parts[1]) or 1
    if "/" in term_id:
        parts = term_id.rsplit("/", 1)
        return parts[0], clean_int(parts[1]) or 1
    return term_id, 1


def _get_cached_term(
    session: Session,
    term_id: str,
    term_cache: set[str] | dict[str, Any] | None,
) -> models.Term | None:
    """Resolve an already-cached term from either a dict or set cache."""
    if isinstance(term_cache, dict) and term_id in term_cache:
        cached = term_cache[term_id]
        if isinstance(cached, models.Term):
            return cached
    if isinstance(term_cache, set) and term_id in term_cache:
        term_in_session = session.get(models.Term, term_id) if hasattr(session, "get") else None
        return term_in_session or session.query(models.Term).filter(models.Term.id == term_id).first()
    return None


def ensure_term(
    session: Session,
    term_id: str,
    term_cache: set[str] | dict[str, Any] | None = None,
) -> models.Term:
    """Ensure academic term exists in database, supporting dict or set caches."""
    cached_term = _get_cached_term(session, term_id, term_cache)
    if cached_term is not None:
        return cached_term

    term = session.query(models.Term).filter(models.Term.id == term_id).first()
    if not term:
        year, sem = _parse_term_parts(term_id)
        term = models.Term(id=term_id, academic_year=year, semester_num=sem)
        session.add(term)
        session.flush()

    if isinstance(term_cache, set):
        term_cache.add(term_id)
    elif isinstance(term_cache, dict):
        term_cache[term_id] = term
    return term


def _maybe_upgrade_department_name(
    session: Session,
    dept: models.Department,
    bolum: str | None,
) -> None:
    """Upgrade placeholder department name (where `bolum == kisaadi`) when resolved."""
    if bolum and dept.bolum == dept.kisaadi and bolum != dept.bolum:
        dept.bolum = bolum
        session.flush()


def _resolve_cached_department(
    session: Session,
    clean_kisaadi: str,
    bolum: str | None,
    dept_cache: dict[str, str] | dict[str, models.Department] | None,
) -> models.Department | None:
    """Resolve department from either `Dict[str, Department]` or legacy `Dict[str, str]`."""
    if dept_cache is None or clean_kisaadi not in dept_cache:
        return None
    cached = dept_cache[clean_kisaadi]
    if isinstance(cached, models.Department):
        _maybe_upgrade_department_name(session, cached, bolum)
        return cached
    if isinstance(cached, str):
        dept_in_session = session.get(models.Department, clean_kisaadi) if hasattr(session, "get") else None
        dept = dept_in_session or session.query(models.Department).filter(
            models.Department.kisaadi == clean_kisaadi
        ).first()
        if dept:
            _maybe_upgrade_department_name(session, dept, bolum)
            dept_cache[clean_kisaadi] = dept.bolum
            return dept
    return None


def ensure_department(
    session: Session,
    dept_kisaadi: str,
    bolum: str | None = None,
    dept_cache: dict[str, str] | dict[str, models.Department] | None = None,
) -> models.Department | None:
    """Ensure academic department exists, rejecting invalid numeric codes."""
    if not dept_kisaadi or not str(dept_kisaadi).strip():
        return None
    clean_kisaadi = str(dept_kisaadi).strip().upper()[:10]
    if any(ch.isdigit() for ch in clean_kisaadi):
        return None

    cached_dept = _resolve_cached_department(session, clean_kisaadi, bolum, dept_cache)
    if cached_dept is not None:
        return cached_dept

    dept = session.query(models.Department).filter(models.Department.kisaadi == clean_kisaadi).first()
    if not dept:
        dept = models.Department(kisaadi=clean_kisaadi, bolum=bolum or clean_kisaadi)
        session.add(dept)
        session.flush()
    else:
        _maybe_upgrade_department_name(session, dept, bolum)

    if dept_cache is not None:
        dept_cache[clean_kisaadi] = dept
    return dept


def ensure_instructor(
    session: Session,
    full_name: str | None,
    inst_cache: dict[str, int] | None = None
) -> int | None:
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
    room_name: str | None,
    room_cache: dict[str, int] | None = None
) -> int | None:
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


_DAY_SORT_ORDER: dict[str, int] = {
    "M": 0,
    "T": 1,
    "W": 2,
    "Th": 3,
    "F": 4,
    "St": 5,
    "Su": 6,
}


def _normalize_day_code(day_raw: str) -> str | None:
    if day_raw in VALID_DAYS:
        return day_raw
    cap = day_raw.capitalize()
    return cap if cap in VALID_DAYS else None


def _parse_raw_slots(slots_payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate and normalize raw slot dicts before forward-fill."""
    parsed_slots: list[dict[str, Any]] = []
    for s in slots_payload:
        slot_hour = clean_int(s.get("hour") or s.get("slot_hour"))
        if slot_hour is None or slot_hour < 1 or slot_hour > 14:
            continue
        day_raw = (s.get("day") or s.get("day_code") or "").strip()
        day_code = _normalize_day_code(day_raw) if day_raw else None
        if not day_code:
            continue
        room_name = (s.get("room") or s.get("room_name") or "").strip()
        clean_room = room_name if room_name and room_name.upper() != "N/A" else None
        parsed_slots.append({
            "day_code": day_code,
            "slot_hour": slot_hour,
            "slot_title": s.get("slot_title"),
            "room_name": clean_room,
        })
    return parsed_slots


def _sync_course_slots(
    session: Session,
    course_id: int,
    slots_payload: list[dict[str, Any]] | None,
    room_cache: dict[str, int],
    dry_run: bool = False
) -> None:
    """Sync course slots, forward-filling rooms strictly within contiguous same-day, same-session hours."""
    if slots_payload is None or dry_run:
        return

    session.query(models.CourseSlot).filter(models.CourseSlot.course_id == course_id).delete(synchronize_session="fetch")
    parsed_slots = _parse_raw_slots(slots_payload)

    # Forward-fill contiguous hours strictly within the same (day_code, normalized slot_title) block
    block_groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for ps in parsed_slots:
        title_key = (ps["slot_title"] or "").strip().lower()
        block_groups.setdefault((ps["day_code"], title_key), []).append(ps)

    for day_slots in block_groups.values():
        day_slots.sort(key=lambda x: x["slot_hour"])
        curr_room: str | None = None
        curr_hour: int | None = None
        for ps in day_slots:
            hr = ps["slot_hour"]
            r_name = ps["room_name"]
            if not r_name and curr_room and curr_hour is not None and hr == curr_hour + 1:
                ps["room_name"] = curr_room
            elif r_name and r_name.upper() != "TBA":
                curr_room = r_name
            elif curr_hour != hr:
                curr_room = None
            curr_hour = hr

            room_id = ensure_room(session, ps["room_name"], room_cache) if ps["room_name"] else None
            session.add(
                models.CourseSlot(
                    course_id=course_id,
                    day_code=ps["day_code"],
                    slot_hour=ps["slot_hour"],
                    slot_title=ps["slot_title"],
                    room_id=room_id,
                )
            )

    session.flush()


def _parse_shifted_hours(raw_delivery: str) -> list[int]:
    """Parse concatenated period digits (1..14) from shifted delivery_method strings."""
    if not raw_delivery.isdigit():
        return []
    hours: list[int] = []
    i = 0
    n = len(raw_delivery)
    while i < n:
        if (
            i + 2 <= n
            and 10 <= int(raw_delivery[i : i + 2]) <= 14
            and (raw_delivery[i + 1] == "0" or i + 2 == n or raw_delivery[i + 2] != "0")
        ):
            hours.append(int(raw_delivery[i : i + 2]))
            i += 2
            continue
        one = int(raw_delivery[i])
        if 1 <= one <= 9:
            hours.append(one)
        i += 1
    return hours


def _sanitize_shifted_payload(val_payload: dict[str, Any]) -> dict[str, Any]:
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
        not any(clean_int(s.get("hour") or s.get("slot_hour")) is not None for s in slots) and
        all(len(str(s.get("day", s.get("day_code", "")))) == 1 for s in slots)
    )

    if not is_shifted:
        return val_payload

    p = dict(val_payload)
    reconstructed_inst = "".join(s.get("day", s.get("day_code", "")) for s in slots if s.get("day") or s.get("day_code")).strip()
    p["instructor"] = reconstructed_inst if reconstructed_inst else "TBA"

    hours = []
    if raw_delivery.isdigit():
        hours = _parse_shifted_hours(raw_delivery)
        p["delivery_method"] = ""

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


_COURSE_ENRICHMENT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("desc_url", "TEXT"),
    ("syllabus_url", "TEXT"),
    ("syllabus_hash", "VARCHAR(64)"),
    ("syllabus_text", "TEXT"),
    ("has_syllabus", "BOOLEAN DEFAULT FALSE NOT NULL"),
)


def _widen_pg_change_columns(engine: Any) -> None:
    """Idempotently widen legacy CourseChange column limits on PostgreSQL only when needed."""
    if getattr(getattr(engine, "dialect", None), "name", None) != "postgresql":
        return
    try:
        cols = {c["name"]: c for c in sa_inspect(engine).get_columns("course_changes")}
        ct_len = getattr(cols.get("change_type", {}).get("type"), "length", None)
        det_type = str(cols.get("details", {}).get("type", "")).upper()
        stmts: list[str] = []
        if ct_len is not None and ct_len < 32:
            stmts.append("ALTER TABLE course_changes ALTER COLUMN change_type TYPE VARCHAR(32)")
        if "TEXT" not in det_type:
            stmts.append("ALTER TABLE course_changes ALTER COLUMN details TYPE TEXT")
        if stmts:
            with engine.begin() as conn:
                for stmt in stmts:
                    conn.execute(text(stmt))
    except Exception as e:
        logger.warning("Could not widen course_changes columns: %s", e)


def ensure_schema_columns(engine: Any) -> None:
    """Ensure tables and additive v0.2.0 enrichment columns exist without breaking live DBs."""
    models.Base.metadata.create_all(bind=engine)
    is_pg = getattr(getattr(engine, "dialect", None), "name", None) == "postgresql"
    existing_cols = {c["name"] for c in sa_inspect(engine).get_columns("courses")}
    missing = [(col, ddl) for col, ddl in _COURSE_ENRICHMENT_COLUMNS if col not in existing_cols]
    if missing:
        add_clause = "ADD COLUMN IF NOT EXISTS" if is_pg else "ADD COLUMN"
        with engine.begin() as conn:
            for col, ddl in missing:
                conn.execute(text(f"ALTER TABLE courses {add_clause} {col} {ddl}"))
    _widen_pg_change_columns(engine)


def _sanitize_http_url(val: Any) -> str | None:
    """Accept only http(s) URLs with a valid host, no whitespace/CRLF, up to 2048 characters."""
    if not val:
        return None
    clean = str(val).strip()
    if len(clean) > 2048 or any(ch in clean for ch in ("\r", "\n", "\t", " ")):
        return None
    parsed = urllib.parse.urlsplit(clean)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return clean
    return None


def upsert_course_catalog(
    session: Session,
    course_code: str | None,
    payload: dict[str, Any],
    catalog_seen: set[str] | None = None,
    dry_run: bool = False,
) -> models.CourseCatalog | None:
    """Upsert bilingual university catalog description metadata keyed by course_code."""
    code = normalize_code(course_code)
    if not code or (catalog_seen is not None and code in catalog_seen) or not isinstance(payload, dict):
        return None

    en_url = _sanitize_http_url(payload.get("catalog_en_url") or payload.get("en_url"))
    tr_url = _sanitize_http_url(payload.get("catalog_tr_url") or payload.get("tr_url"))
    en_text = (payload.get("catalog_en_text") or payload.get("en_text") or "").strip() or None
    tr_text = (payload.get("catalog_tr_text") or payload.get("tr_text") or "").strip() or None
    canonical_text = (
        (payload.get("catalog_text") or payload.get("canonical_text") or "").strip()
        or "\n\n".join(t for t in (en_text, tr_text) if t)
        or None
    )
    content_hash = (payload.get("catalog_hash") or payload.get("content_hash") or "").strip() or None
    title = (payload.get("title") or payload.get("course_name") or "").strip() or None
    updated_at = payload.get("updated_at") or datetime.now(UTC).isoformat()

    if not any((en_text, tr_text, canonical_text, en_url, tr_url, content_hash)):
        return None
    if dry_run:
        return None

    catalog = session.query(models.CourseCatalog).filter(models.CourseCatalog.course_code == code).first()
    cat_fields = {
        "title": title[:255] if title else None,
        "en_url": en_url,
        "tr_url": tr_url,
        "en_text": en_text,
        "tr_text": tr_text,
        "canonical_text": canonical_text,
        "content_hash": content_hash[:64] if content_hash else None,
        "updated_at": str(updated_at)[:50],
    }
    if not catalog:
        catalog = models.CourseCatalog(course_code=code, **cat_fields)
        session.add(catalog)
    else:
        for field, value in cat_fields.items():
            if value is not None:
                setattr(catalog, field, value)

    if catalog_seen is not None:
        catalog_seen.add(code)
    session.flush()
    return catalog


def _apply_course_updates(
    course: models.Course,
    updates: dict[str, Any],
    clear_fields: set[str] | None = None,
) -> None:
    """Apply non-None course attribute updates and explicit clears in place."""
    clears = clear_fields or set()
    for field, value in updates.items():
        if value is not None or field in clears:
            setattr(course, field, value)


def _extract_enrichment_fields(
    val_payload: dict[str, Any],
    is_new: bool,
    existing_course: models.Course | None = None,
) -> tuple[dict[str, Any], set[str]]:
    """Extract course syllabus and description metadata without clobbering existing values on partial deltas."""
    fields: dict[str, Any] = {}
    clear_fields: set[str] = set()

    if "desc_url" in val_payload or "description_link_url" in val_payload:
        raw_desc = val_payload.get("desc_url") if "desc_url" in val_payload else val_payload.get("description_link_url")
        fields["desc_url"] = _sanitize_http_url(raw_desc)
        if raw_desc == "":
            clear_fields.add("desc_url")

    if "syllabus_url" in val_payload:
        raw_syl = val_payload.get("syllabus_url")
        fields["syllabus_url"] = _sanitize_http_url(raw_syl)
        if raw_syl == "":
            clear_fields.add("syllabus_url")

    if "syllabus_hash" in val_payload:
        raw_hash = (val_payload.get("syllabus_hash") or "").strip()
        fields["syllabus_hash"] = raw_hash[:64] if raw_hash else None
        if raw_hash == "":
            clear_fields.add("syllabus_hash")

    if "syllabus_text" in val_payload:
        raw_text = (val_payload.get("syllabus_text") or "").strip()
        fields["syllabus_text"] = raw_text or None
        if raw_text == "":
            clear_fields.add("syllabus_text")

    has_syl_signal = any(k in val_payload for k in ("has_syllabus", "syllabus_url", "syllabus_hash", "syllabus_text"))
    if is_new or has_syl_signal:
        eff_url = fields["syllabus_url"] if "syllabus_url" in fields else getattr(existing_course, "syllabus_url", None)
        eff_hash = fields["syllabus_hash"] if "syllabus_hash" in fields else getattr(existing_course, "syllabus_hash", None)
        eff_text = fields["syllabus_text"] if "syllabus_text" in fields else getattr(existing_course, "syllabus_text", None)
        fields["has_syllabus"] = bool(val_payload.get("has_syllabus") or eff_url or eff_hash or eff_text)

    return fields, clear_fields


def _normalize_course_department(
    session: Session,
    dept_kisaadi: str | None,
    dept_cache: dict[str, str] | dict[str, models.Department] | None,
) -> str | None:
    """Validate and ensure course department exists, returning canonical code or None."""
    if not dept_kisaadi or not str(dept_kisaadi).strip():
        return None
    dept = ensure_department(session, str(dept_kisaadi).strip().upper(), dept_cache=dept_cache)
    return dept.kisaadi if dept else None


def _upsert_course(
    session: Session,
    term_id: str,
    dept_kisaadi: str | None,
    course_code: str,
    section: str | None,
    val_payload: dict[str, Any],
    inst_cache: dict[str, int],
    room_cache: dict[str, int],
    dept_cache: dict[str, str] | dict[str, models.Department] | None = None,
    term_cache: set[str] | dict[str, Any] | None = None,
    dry_run: bool = False,
    catalog_seen: set[str] | None = None,
) -> models.Course | None:
    """Upsert course, optional syllabus metadata, catalog description, and session slots."""
    val_payload = _sanitize_shifted_payload(val_payload)
    ensure_term(session, term_id, term_cache)
    normalized_dept = _normalize_course_department(session, dept_kisaadi, dept_cache)

    course = session.query(models.Course).filter(
        models.Course.term_id == term_id,
        models.Course.course_code == course_code,
        models.Course.section == section,
    ).first()

    is_new = course is None
    raw_inst = val_payload.get("instructor")
    fields: dict[str, Any] = {
        "dept_kisaadi": normalized_dept,
        "title": val_payload.get("course_name") or val_payload.get("title"),
        "instructor_id": ensure_instructor(session, raw_inst, inst_cache),
        "credits": clean_int(val_payload.get("credits")),
        "ects": clean_int(val_payload.get("ects")),
        "delivery_method": val_payload.get("delivery_method"),
    }
    enrichment_fields, clear_fields = _extract_enrichment_fields(
        val_payload, is_new=is_new, existing_course=course
    )
    if "instructor" in val_payload and (raw_inst is None or str(raw_inst).strip().upper() in ("", "TBA")):
        clear_fields.add("instructor_id")
    fields.update(enrichment_fields)

    if course is None:
        course = models.Course(term_id=term_id, course_code=course_code, section=section, **fields)
        if not dry_run:
            session.add(course)
    else:
        _apply_course_updates(course, fields, clear_fields=clear_fields)

    if not dry_run:
        session.flush()
        upsert_course_catalog(session, course_code, val_payload, catalog_seen=catalog_seen, dry_run=dry_run)

    if "slots" in val_payload:
        slots_payload = val_payload["slots"]
    elif "course_slots" in val_payload:
        slots_payload = val_payload["course_slots"]
    else:
        slots_payload = None
    if course and course.id:
        _sync_course_slots(session, course.id, slots_payload, room_cache, dry_run=dry_run)

    return course


SUBJECT_PREFIX_TO_DEPT: dict[str, str] = {
    "FA": "LL",
    "EL": "LL",
    "CL": "LL",
    "AL": "LL",
    "LIT": "LL",
    "CRIT": "LL",
    "DRA": "LL",
    "HUM": "LL",
    "ESC": "ENV",
    "ADEX": "XMBA",
    "SFL": "YADYOK",
    "AE": "YADYOK",
    "GER": "YADYOK",
    "FR": "YADYOK",
    "SPA": "YADYOK",
    "ITA": "YADYOK",
    "RUS": "YADYOK",
    "ARA": "YADYOK",
    "PER": "YADYOK",
    "CHI": "YADYOK",
    "ARM": "YADYOK",
    "KUR": "YADYOK",
    "TK": "TKL",
    "TKF": "TKL",
    "TKR": "TKL",
}


def _resolve_dept_for_course(
    session: Session,
    raw_dept: str | None,
    course_code: str | None,
    term_id: str | None = None,
    section: str | None = None,
) -> str | None:
    if raw_dept and str(raw_dept).strip():
        cand = str(raw_dept).strip().upper()
        if not any(c.isdigit() for c in cand):
            return cand

    if not course_code:
        return None

    # Check if this course_code already has an authoritative dept_kisaadi in PostgreSQL
    existing = (
        session.query(models.Course.dept_kisaadi)
        .filter(
            models.Course.course_code == course_code,
            models.Course.dept_kisaadi.isnot(None),
        )
        .order_by(models.Course.term_id.desc())
        .first()
    )
    if existing and existing[0]:
        return str(existing[0]).strip().upper()

    match = re.match(r"^([A-Za-z]+)", course_code.strip())
    if match:
        prefix = match.group(1).upper()
        return SUBJECT_PREFIX_TO_DEPT.get(prefix, prefix)
    return None


_UPSERT_CHANGE_TYPES = frozenset({
    "added", "insert", "inserted", "create", "created",
    "modified", "update", "updated", "modify",
    "room_changed", "slots_changed", "instructor_changed", "syllabus_changed",
})
_REMOVE_CHANGE_TYPES = frozenset({"removed", "delete", "deleted", "remove", "drop", "dropped"})
_FLAT_COURSE_KEYS = (
    "course_name", "title", "instructor", "credits", "ects", "slots", "course_slots",
    "syllabus_url", "syllabus_hash", "desc_url", "description_link_url",
)


def _record_course_change(
    session: Session,
    item: dict[str, Any],
    term_id: str,
    dept_kisaadi: str | None,
    course_code: str,
    section: str | None,
    timestamp: str,
) -> None:
    """Persist a CourseChange audit record for a delta event."""
    raw_type = str(item.get("change_type") or "")[:32]
    details = item.get("details")
    session.add(
        models.CourseChange(
            change_type=raw_type,
            term_id=term_id,
            dept_kisaadi=dept_kisaadi,
            course_code=course_code,
            section=section,
            timestamp=timestamp,
            old_value=json.dumps(item.get("old_value")) if item.get("old_value") else None,
            new_value=json.dumps(item.get("new_value")) if item.get("new_value") else None,
            details=str(details)[:4000] if details is not None else None,
        )
    )


def _extract_delta_payload(item: dict[str, Any]) -> dict[str, Any]:
    """Return nested `new_value` or flat delta item payload when present."""
    val_payload = item.get("new_value") or {}
    if not val_payload and any(k in item for k in _FLAT_COURSE_KEYS):
        return item
    return val_payload


def _apply_room_only_delta(
    session: Session,
    term_id: str,
    course_code: str,
    section: str | None,
    rooms_list: list[Any],
    room_cache: dict[str, int],
    touched_course_ids: set[int] | None,
    dry_run: bool,
) -> int | None:
    """Update existing CourseSlot room assignments from a `ROOM_CHANGED` delta payload."""
    course = session.query(models.Course).filter(
        models.Course.term_id == term_id,
        models.Course.course_code == course_code,
        models.Course.section == section,
    ).first()
    if not course:
        return None
    if not dry_run:
        sorted_slots = sorted(
            course.slots,
            key=lambda s: (
                _DAY_SORT_ORDER.get(s.day_code or "", 99),
                s.day_code or "",
                s.slot_hour or 0,
                s.slot_title or "",
            ),
        )
        if len(rooms_list) != len(sorted_slots):
            logger.warning(
                "Skipping positional ROOM_CHANGED for %s %s.%s: %d rooms != %d slots",
                term_id,
                course_code,
                section,
                len(rooms_list),
                len(sorted_slots),
            )
            return None
        for slot, raw_room in zip(sorted_slots, rooms_list):
            r_name = str(raw_room or "").strip()
            slot.room_id = ensure_room(session, r_name, room_cache) if r_name and r_name.upper() != "N/A" else None
        session.flush()
    if touched_course_ids is not None:
        touched_course_ids.add(course.id)
    return course.id


def _apply_description_delta(
    session: Session,
    term_id: str,
    course_code: str,
    section: str | None,
    val_payload: dict[str, Any],
    catalog_fetcher: Callable[[str], dict[str, Any] | None] | None,
    touched_course_ids: set[int] | None,
    dry_run: bool,
) -> int | None:
    """Update course description link and `CourseCatalog` entry on `DESCRIPTION_CHANGED`."""
    courses = session.query(models.Course).filter(
        models.Course.term_id == term_id,
        models.Course.course_code == course_code,
    ).all()
    if not dry_run:
        desc_url = _sanitize_http_url(val_payload.get("description_link_url") or val_payload.get("desc_url"))
        if "description_link_url" in val_payload or "desc_url" in val_payload:
            for c in courses:
                if section is None or c.section == section:
                    c.desc_url = desc_url
        has_inline_cat = any(
            val_payload.get(k) for k in ("en_text", "tr_text", "canonical_text", "catalog_text", "catalog_en_text", "catalog_tr_text")
        )
        cat_payload = dict(val_payload)
        if not has_inline_cat and catalog_fetcher is not None:
            try:
                fetched = catalog_fetcher(course_code)
                if isinstance(fetched, dict):
                    cat_payload = {**cat_payload, **fetched}
            except Exception as e:
                logger.warning("Catalog fetch failed for %s: %s", course_code, e)
        upsert_course_catalog(session, course_code, cat_payload, dry_run=False)
        session.flush()

    if touched_course_ids is not None:
        for c in courses:
            touched_course_ids.add(c.id)
    return courses[0].id if courses else None


def _remove_course_from_delta(
    session: Session,
    term_id: str,
    course_code: str,
    section: str | None,
    deleted_course_ids: set[int] | None,
    dry_run: bool,
) -> int | None:
    """Delete a removed course section from PostgreSQL and queue post-commit Meilisearch cleanup."""
    course = session.query(models.Course).filter(
        models.Course.term_id == term_id,
        models.Course.course_code == course_code,
        models.Course.section == section,
    ).first()
    if not course or dry_run:
        return None
    course_id = course.id
    session.query(models.CourseSlot).filter(models.CourseSlot.course_id == course_id).delete(
        synchronize_session="fetch"
    )
    session.delete(course)
    session.flush()
    if deleted_course_ids is not None:
        deleted_course_ids.add(course_id)
    return course_id


def _is_room_only_delta(change_type: str, val_payload: dict[str, Any]) -> bool:
    return (
        change_type == "room_changed"
        and "slots" not in val_payload
        and "course_slots" not in val_payload
        and isinstance(val_payload.get("rooms"), list)
    )


def _handle_course_removal_delta(
    session: Session,
    term_id: str,
    course_code: str,
    section: str | None,
    touched_course_ids: set[int] | None,
    deleted_course_ids: set[int] | None,
    meili_index: Any,
    dry_run: bool,
) -> None:
    removed_id = _remove_course_from_delta(
        session, term_id, course_code, section, deleted_course_ids, dry_run
    )
    if removed_id is None:
        return
    if touched_course_ids is not None:
        touched_course_ids.discard(removed_id)
    if deleted_course_ids is None and meili_index:
        try:
            meili_index.delete_document(removed_id)
        except Exception as e:
            logger.warning("Meilisearch delete error for course %s: %s", removed_id, e)


def _resolve_delta_caches(
    session: Session,
    inst_cache: dict[str, int] | None,
    room_cache: dict[str, int] | None,
    dept_cache: dict[str, str] | dict[str, models.Department] | None,
    term_cache: set[str] | dict[str, Any] | None,
) -> tuple[dict[str, int], dict[str, int], dict[str, str] | dict[str, models.Department], set[str] | dict[str, Any]]:
    return (
        inst_cache if inst_cache is not None else {i.full_name: i.id for i in session.query(models.Instructor).all()},
        room_cache if room_cache is not None else {r.name: r.id for r in session.query(models.Room).all()},
        dept_cache if dept_cache is not None else {d.kisaadi: d for d in session.query(models.Department).all()},
        term_cache if term_cache is not None else {t.id: t for t in session.query(models.Term).all()},
    )


def apply_delta_event(
    session: Session,
    item: dict[str, Any],
    inst_cache: dict[str, int] | None = None,
    room_cache: dict[str, int] | None = None,
    dept_cache: dict[str, str] | dict[str, models.Department] | None = None,
    term_cache: set[str] | dict[str, Any] | None = None,
    touched_course_ids: set[int] | None = None,
    meili_index=None,
    dry_run: bool = False,
    catalog_fetcher: Callable[[str], dict[str, Any] | None] | None = None,
    deleted_course_ids: set[int] | None = None,
) -> int | None:
    """Apply a discrete course delta event to PostgreSQL."""
    raw_change_type = item.get("change_type")
    term_id = item.get("term")
    course_code = normalize_code(item.get("course_code"))
    if not raw_change_type or not term_id or not course_code:
        return None

    section = normalize_section(item.get("section"))
    dept_kisaadi = _resolve_dept_for_course(
        session, item.get("department"), course_code, term_id=term_id, section=section
    )
    timestamp = item.get("timestamp") or datetime.now(UTC).isoformat()
    inst_cache, room_cache, dept_cache, term_cache = _resolve_delta_caches(
        session, inst_cache, room_cache, dept_cache, term_cache
    )

    if not dry_run:
        _record_course_change(session, item, term_id, dept_kisaadi, course_code, section, timestamp)

    change_type = str(raw_change_type).strip().lower()
    val_payload = _extract_delta_payload(item)
    if _is_room_only_delta(change_type, val_payload):
        return _apply_room_only_delta(
            session, term_id, course_code, section, val_payload["rooms"], room_cache, touched_course_ids, dry_run
        )
    if change_type == "description_changed":
        return _apply_description_delta(
            session, term_id, course_code, section, val_payload, catalog_fetcher, touched_course_ids, dry_run
        )
    if change_type in _UPSERT_CHANGE_TYPES:
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
            dry_run=dry_run,
        )
        if course and course.id:
            if touched_course_ids is not None:
                touched_course_ids.add(course.id)
            return course.id
    elif change_type in _REMOVE_CHANGE_TYPES:
        _handle_course_removal_delta(
            session, term_id, course_code, section, touched_course_ids, deleted_course_ids, meili_index, dry_run
        )

    return None


def _load_catalog_text_map(courses: list[models.Course]) -> dict[str, str]:
    """Batch-load truncated catalog texts for courses attached to an active SQLAlchemy Session."""
    if not courses:
        return {}
    try:
        session = object_session(courses[0])
        if session is None:
            return {}
        codes = list({c.course_code for c in courses if getattr(c, "course_code", None)})
        if not codes:
            return {}
        rows = session.query(models.CourseCatalog.course_code, models.CourseCatalog.canonical_text).filter(
            models.CourseCatalog.course_code.in_(codes)
        ).all()
        return {code: (text_val or "")[:4000] for code, text_val in rows}
    except Exception:
        return {}


def _build_meili_document(c: models.Course, catalog_map: dict[str, str]) -> dict[str, Any]:
    """Format a Course ORM entity into a Meilisearch search document."""
    slots_data = [
        {
            "day_code": s.day_code,
            "slot_hour": s.slot_hour,
            "slot_title": s.slot_title,
            "room": s.room.name if s.room else None,
            "room_name": s.room.name if s.room else None,
        }
        for s in c.slots
    ]
    dept_code = (
        c.dept_kisaadi.upper()
        if c.dept_kisaadi
        else (c.course_code.split()[0].upper() if c.course_code else None)
    )
    return {
        "id": c.id,
        "term": c.term_id,
        "course_code": c.course_code,
        "section": c.section or "01",
        "title": c.title or "",
        "dept_code": dept_code,
        "department": c.department.bolum if c.department else c.dept_kisaadi,
        "instructor": c.instructor.full_name if c.instructor else "TBA",
        "instructor_id": c.instructor_id,
        "credits": c.credits,
        "ects": c.ects,
        "delivery_method": c.delivery_method or "",
        "has_syllabus": bool(getattr(c, "has_syllabus", False)),
        "syllabus_snippet": (getattr(c, "syllabus_text", None) or "")[:2000],
        "catalog_text": catalog_map.get(c.course_code, ""),
        "slots": slots_data,
    }


def sync_meili_documents(meili_index, courses: list[models.Course], chunk_size: int = 1000):
    """Serialize courses to Meilisearch search documents and push in batches."""
    if not meili_index or not courses:
        return
    catalog_map = _load_catalog_text_map(courses)
    documents = [_build_meili_document(c, catalog_map) for c in courses]

    for i in range(0, len(documents), chunk_size):
        chunk = documents[i:i + chunk_size]
        try:
            meili_index.add_documents(chunk)
            logger.info("Pushed %d document(s) to Meilisearch index", len(chunk))
        except Exception as e:
            logger.error("Failed pushing %d documents to Meilisearch: %s", len(chunk), e)


def apply_deltas_batch(
    session: Session,
    deltas: list[dict[str, Any]],
    meili_index = None,
    dry_run: bool = False
) -> list[int]:
    """Apply a batch of delta events in a single transaction with savepoint cache isolation."""
    touched_ids: set[int] = set()
    deleted_ids: set[int] = set()
    inst_cache = {i.full_name: i.id for i in session.query(models.Instructor).all()}
    room_cache = {r.name: r.id for r in session.query(models.Room).all()}
    dept_cache = {d.kisaadi: d for d in session.query(models.Department).all()}
    term_cache = {t.id: t for t in session.query(models.Term).all()}

    for item in deltas:
        snap_inst = dict(inst_cache)
        snap_room = dict(room_cache)
        snap_dept = dict(dept_cache)
        snap_term = dict(term_cache)
        try:
            with session.begin_nested():
                apply_delta_event(
                    session=session,
                    item=item,
                    inst_cache=inst_cache,
                    room_cache=room_cache,
                    dept_cache=dept_cache,
                    term_cache=term_cache,
                    touched_course_ids=touched_ids,
                    meili_index=None,
                    dry_run=dry_run,
                    deleted_course_ids=deleted_ids,
                )
        except Exception as e:
            inst_cache.clear(); inst_cache.update(snap_inst)
            room_cache.clear(); room_cache.update(snap_room)
            dept_cache.clear(); dept_cache.update(snap_dept)
            term_cache.clear(); term_cache.update(snap_term)
            logger.warning("Error applying delta item %s: %s", item, e)

    if not dry_run:
        session.commit()
        if meili_index and deleted_ids:
            for cid in deleted_ids:
                try:
                    meili_index.delete_document(cid)
                except Exception as e:
                    logger.warning("Meilisearch post-commit delete error for course %s: %s", cid, e)
        if meili_index and touched_ids:
            updated_courses = session.query(models.Course).options(
                joinedload(models.Course.term),
                joinedload(models.Course.department),
                joinedload(models.Course.instructor),
                selectinload(models.Course.slots).joinedload(models.CourseSlot.room)
            ).filter(models.Course.id.in_(touched_ids)).all()
            sync_meili_documents(meili_index, updated_courses)

    return list(touched_ids)


def record_scrape_summary(session: Session, summary: dict[str, Any], dry_run: bool = False) -> None:
    """Record an upstream scrape completion summary."""
    run_id = summary.get("run_id")
    term = summary.get("term")
    completed_at = summary.get("completed_at") or datetime.now(UTC).isoformat()
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
