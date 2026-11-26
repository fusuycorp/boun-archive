import json
import logging
import sys
from typing import Any

from sqlalchemy.orm import Session, joinedload, selectinload

from . import database, models, schemas
from .optimizer import solve_schedule_csp

logger = logging.getLogger("boun_mcp_server")

TOOLS_DEFINITIONS = [
    {
        "name": "boun_search_courses",
        "description": "Search courses, timetables, and instructors across historical semesters at Boğaziçi University.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keyword, course code (e.g. CMPE 150), or instructor name"
                },
                "term": {
                    "type": "string",
                    "description": "Optional semester filter (e.g. 2024/2025-1)"
                },
                "dept": {
                    "type": "string",
                    "description": "Optional department code (e.g. CMPE, MATH, ECON)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default 10, max 50)",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "boun_get_course_history",
        "description": "Retrieve comprehensive historical offerings, past instructors, and time slot patterns for a course code.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "course_code": {
                    "type": "string",
                    "description": "Course code e.g. 'CMPE 150' or 'MATH 101'"
                }
            },
            "required": ["course_code"]
        }
    },
    {
        "name": "boun_get_course_quota",
        "description": "Retrieve the latest real-time or historical quota capacity, current enrollments, and consent status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "course_code": {
                    "type": "string",
                    "description": "Course code e.g. 'CMPE 150'"
                },
                "term": {
                    "type": "string",
                    "description": "Optional academic term identifier"
                }
            },
            "required": ["course_code"]
        }
    },
    {
        "name": "boun_optimize_schedule",
        "description": "Run the deterministic Constraint Satisfaction Problem (CSP) schedule solver to assemble conflict-free weekly timetables.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "term_id": {
                    "type": "string",
                    "description": "Target semester ID e.g. 2024/2025-1"
                },
                "target_courses": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Mandatory course codes (e.g. ['CMPE 150', 'MATH 101'])"
                },
                "candidate_electives": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional elective course pool to pick from"
                },
                "num_electives_needed": {
                    "type": "integer",
                    "description": "How many electives to select from candidate_electives pool",
                    "default": 0
                },
                "avoid_days": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Days to avoid (e.g. ['F', 'M'])"
                },
                "min_hour": {
                    "type": "integer",
                    "description": "Earliest starting hour slot (1-14)",
                    "default": 1
                },
                "max_hour": {
                    "type": "integer",
                    "description": "Latest ending hour slot (1-14)",
                    "default": 14
                },
                "max_campus_days": {
                    "type": "integer",
                    "description": "Maximum number of days on campus per week"
                }
            },
            "required": ["term_id", "target_courses"]
        }
    }
]

def _escape_sql_wildcards(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def execute_tool(name: str, args: dict[str, Any], db: Session) -> dict[str, Any]:
    if not isinstance(args, dict):
        raise ValueError("Tool arguments must be a JSON object")

    if name == "boun_search_courses":
        query_str = str(args.get("query") or "").strip()
        term = args.get("term")
        dept = args.get("dept")
        limit = max(1, min(int(args.get("limit", 10)), 50))

        q = db.query(models.Course).options(
            joinedload(models.Course.instructor),
            selectinload(models.Course.slots).joinedload(models.CourseSlot.room)
        ).join(models.Course.instructor, isouter=True)
        if term:
            q = q.filter(models.Course.term_id == str(term).strip())
        if dept:
            q = q.filter(models.Course.dept_kisaadi == str(dept).strip().upper())
        if query_str:
            escaped = _escape_sql_wildcards(query_str)
            pattern = f"%{escaped}%"
            q = q.filter(
                (models.Course.course_code.ilike(pattern, escape="\\")) |
                (models.Course.title.ilike(pattern, escape="\\")) |
                (models.Instructor.full_name.ilike(pattern, escape="\\"))
            )

        courses = q.order_by(models.Course.term_id.desc(), models.Course.course_code.asc()).limit(limit).all()
        return {
            "count": len(courses),
            "courses": [
                {
                    "course_code": c.course_code,
                    "section": c.section,
                    "term": c.term_id,
                    "title": c.title,
                    "instructor": c.instructor.full_name if c.instructor else "TBA",
                    "credits": c.credits,
                    "ects": c.ects,
                    "slots": [{"day": s.day_code, "hour": s.slot_hour, "room": s.room_name} for s in c.slots]
                }
                for c in courses
            ]
        }

    if name == "boun_get_course_history":
        course_code = str(args.get("course_code") or "").strip()
        clean_code = " ".join(course_code.split()).upper()
        escaped_code = _escape_sql_wildcards(clean_code)
        courses = db.query(models.Course).options(
            joinedload(models.Course.instructor),
            selectinload(models.Course.slots).joinedload(models.CourseSlot.room)
        ).filter(
            models.Course.course_code.ilike(escaped_code, escape="\\")
        ).order_by(models.Course.term_id.desc()).limit(100).all()

        return {
            "course_code": clean_code,
            "total_recorded_offerings": len(courses),
            "history": [
                {
                    "term": c.term_id,
                    "section": c.section,
                    "title": c.title,
                    "instructor": c.instructor.full_name if c.instructor else "TBA",
                    "slots": [{"day": s.day_code, "hour": s.slot_hour, "room": s.room_name} for s in c.slots]
                }
                for c in courses
            ]
        }

    if name == "boun_get_course_quota":
        course_code = str(args.get("course_code") or "").strip()
        term = args.get("term")
        clean_code = " ".join(course_code.split()).upper()
        escaped_code = _escape_sql_wildcards(clean_code)

        q = db.query(models.QuotaSnapshot).filter(
            models.QuotaSnapshot.course_code.ilike(escaped_code, escape="\\")
        )
        if term:
            q = q.filter(models.QuotaSnapshot.term_id == str(term).strip())
        snapshots = q.order_by(models.QuotaSnapshot.captured_at.desc()).limit(50).all()

        return {
            "course_code": clean_code,
            "snapshots": [
                {
                    "term": s.term_id,
                    "section": s.section,
                    "department": s.department,
                    "quota": s.quota,
                    "current": s.current,
                    "available": s.available,
                    "is_consent": s.is_consent,
                    "captured_at": s.captured_at
                }
                for s in snapshots
            ]
        }

    if name == "boun_optimize_schedule":
        req = schemas.ScheduleOptimizationRequest(
            term_id=args.get("term_id", ""),
            target_courses=args.get("target_courses", []),
            candidate_electives=args.get("candidate_electives", []),
            num_electives_needed=args.get("num_electives_needed", 0),
            avoid_days=args.get("avoid_days", []),
            min_hour=args.get("min_hour", 1),
            max_hour=args.get("max_hour", 14),
            max_campus_days=args.get("max_campus_days"),
            max_results=args.get("max_results", 5)
        )
        res = solve_schedule_csp(db, req)
        return res.model_dump()

    raise ValueError(f"Unknown tool: {name}")


def _execute_mcp_tool_call(msg_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(params, dict):
        params = {}
    tool_name = params.get("name")
    tool_args = params.get("arguments", {})
    db = database.SessionLocal()
    try:
        tool_res = execute_tool(tool_name, tool_args, db)
        result = {
            "content": [{"type": "text", "text": json.dumps(tool_res, indent=2, ensure_ascii=False)}],
            "isError": False,
        }
    except Exception as ex:
        db.rollback()
        result = {
            "content": [{"type": "text", "text": f"Error executing {tool_name}: {ex!s}"}],
            "isError": True,
        }
    finally:
        db.close()
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _dispatch_mcp_message(msg: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(msg, dict):
        return None
    msg_id = msg.get("id")
    method = msg.get("method")
    params = msg.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "boun-archive-mcp", "version": "1.0.0"},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS_DEFINITIONS}}
    if method == "tools/call":
        return _execute_mcp_tool_call(msg_id, params)
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    return None


def run_stdio_mcp_server():
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception as e:
            logger.error(f"Invalid JSON: {e}")
            continue
        if not isinstance(msg, dict):
            logger.warning("Ignoring non-object JSON-RPC frame")
            continue

        resp = _dispatch_mcp_message(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_stdio_mcp_server()
