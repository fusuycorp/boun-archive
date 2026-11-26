import time
from itertools import combinations
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from . import models, schemas

DAY_ORDER = ["M", "T", "W", "Th", "F", "St", "Su"]

class SectionSlotData:
    def __init__(
        self,
        course_id: int,
        course_code: str,
        section: str,
        title: str,
        instructor: str,
        credits: int | None,
        ects: int | None,
        slots: list[dict[str, Any]]
    ):
        self.course_id = course_id
        self.course_code = course_code
        self.section = section
        self.title = title
        self.instructor = instructor
        self.credits = credits or 0
        self.ects = ects or 0
        self.slots = slots
        self.occupied_slots: set[tuple[str, int]] = {
            (s["day_code"], int(s["slot_hour"]))
            for s in slots
            if s.get("day_code") and s.get("slot_hour") is not None
        }

    def has_conflict(self, other: "SectionSlotData") -> bool:
        return bool(self.occupied_slots.intersection(other.occupied_slots))


def calculate_schedule_metrics(selected_sections: list[SectionSlotData]) -> dict[str, Any]:
    day_hours: dict[str, list[int]] = {}
    for sec in selected_sections:
        for s in sec.slots:
            d = s.get("day_code")
            h = s.get("slot_hour")
            if d and h is not None:
                day_hours.setdefault(d, []).append(int(h))

    campus_days = [d for d in DAY_ORDER if d in day_hours]
    total_gaps = 0
    for d, hours in day_hours.items():
        if len(hours) > 1:
            sorted_h = sorted(set(hours))
            span = sorted_h[-1] - sorted_h[0] + 1
            gaps = span - len(sorted_h)
            total_gaps += max(0, gaps)

    score = 100.0 - (total_gaps * 5.0) - (len(campus_days) * 8.0)
    tba_count = sum(1 for sec in selected_sections if sec.instructor in ("TBA", "STAFF", "N/A"))
    score -= tba_count * 4.0

    return {
        "score": round(max(0.0, score), 2),
        "campus_days": campus_days,
        "total_gap_hours": total_gaps,
        "total_credits": sum(sec.credits for sec in selected_sections),
        "total_ects": sum(sec.ects for sec in selected_sections)
    }


def fetch_course_sections(
    db: Session,
    term_id: str,
    course_codes: list[str]
) -> dict[str, list[SectionSlotData]]:
    results: dict[str, list[SectionSlotData]] = {}
    
    clean_codes = [" ".join(c.strip().split()).upper() for c in course_codes if c.strip()]
    if not clean_codes:
        return results

    courses = db.query(models.Course).options(
        joinedload(models.Course.instructor),
        joinedload(models.Course.slots).joinedload(models.CourseSlot.room)
    ).filter(
        models.Course.term_id == term_id,
        func.upper(models.Course.course_code).in_(clean_codes)
    ).order_by(models.Course.course_code, models.Course.section).all()

    for c in courses:
        code_key = c.course_code.upper()
        slots_data = [{
            "day_code": s.day_code,
            "slot_hour": s.slot_hour,
            "slot_title": s.slot_title,
            "room_name": s.room.name if s.room else "N/A"
        } for s in c.slots]

        sec_data = SectionSlotData(
            course_id=c.id,
            course_code=c.course_code,
            section=c.section or "01",
            title=c.title or c.course_code,
            instructor=c.instructor.full_name if c.instructor else "TBA",
            credits=c.credits,
            ects=c.ects,
            slots=slots_data
        )
        results.setdefault(code_key, []).append(sec_data)

    return results


_MAX_TIMEOUT_SECONDS = 5.0
_MAX_EXPLORED_STATES = 10000
_MAX_COLLECTED_RESULTS = 500


def _filter_sections_by_constraints(
    sections_by_course: dict[str, list[SectionSlotData]],
    request: schemas.ScheduleOptimizationRequest,
) -> dict[str, list[SectionSlotData]]:
    avoid_days_set = set(request.avoid_days)
    filtered_by_course: dict[str, list[SectionSlotData]] = {}
    for code, sec_list in sections_by_course.items():
        valid_secs = []
        for sec in sec_list:
            hours = [h for _, h in sec.occupied_slots]
            if hours and (min(hours) < request.min_hour or max(hours) > request.max_hour):
                continue
            if avoid_days_set and any(d in avoid_days_set for d, _ in sec.occupied_slots):
                continue
            valid_secs.append(sec)
        filtered_by_course[code] = valid_secs
    return filtered_by_course


def _build_candidate_groups(
    required_keys: list[str], elective_keys: list[str], num_electives: int
) -> list[list[str]]:
    if num_electives <= 0:
        return [required_keys]
    groups: list[list[str]] = []
    for elect_comb in combinations(elective_keys, num_electives):
        groups.append(required_keys + list(elect_comb))
        if len(groups) >= 50:
            break
    return groups


def _limits_reached(valid_count: int, states_count: int, start_time: float) -> bool:
    return (
        valid_count >= _MAX_COLLECTED_RESULTS
        or states_count >= _MAX_EXPLORED_STATES
        or time.monotonic() - start_time > _MAX_TIMEOUT_SECONDS
    )


def _search_course_group(
    course_list: list[str],
    index: int,
    current_assignment: list[SectionSlotData],
    current_occupied: set[tuple[str, int]],
    current_days: set[str],
    filtered_by_course: dict[str, list[SectionSlotData]],
    max_campus_days: int | None,
    valid_combinations: list[dict[str, Any]],
    states_count: list[int],
    start_time: float,
) -> None:
    if _limits_reached(len(valid_combinations), states_count[0], start_time):
        return
    states_count[0] += 1
    if index == len(course_list):
        metrics = calculate_schedule_metrics(current_assignment)
        if not (max_campus_days and len(metrics["campus_days"]) > max_campus_days):
            valid_combinations.append({"sections": list(current_assignment), "metrics": metrics})
        return

    for sec in filtered_by_course.get(course_list[index], []):
        if sec.occupied_slots.intersection(current_occupied):
            continue
        next_days = current_days.union(d for d, _ in sec.occupied_slots)
        if max_campus_days and len(next_days) > max_campus_days:
            continue
        _search_course_group(
            course_list,
            index + 1,
            current_assignment + [sec],
            current_occupied.union(sec.occupied_slots),
            next_days,
            filtered_by_course,
            max_campus_days,
            valid_combinations,
            states_count,
            start_time,
        )
        if len(valid_combinations) >= _MAX_COLLECTED_RESULTS or states_count[0] >= _MAX_EXPLORED_STATES:
            break


def _run_csp_backtrack(
    candidate_group_sets: list[list[str]],
    filtered_by_course: dict[str, list[SectionSlotData]],
    max_campus_days: int | None,
) -> list[dict[str, Any]]:
    start_time = time.monotonic()
    valid_combinations: list[dict[str, Any]] = []
    states_count = [0]

    for group_set in candidate_group_sets:
        _search_course_group(
            group_set,
            0,
            [],
            set(),
            set(),
            filtered_by_course,
            max_campus_days,
            valid_combinations,
            states_count,
            start_time,
        )
        if _limits_reached(len(valid_combinations), states_count[0], start_time):
            break
    return valid_combinations


def _serialize_combinations(top_results: list[dict[str, Any]]) -> list[schemas.TimetableCombination]:
    result_combinations: list[schemas.TimetableCombination] = []
    for item in top_results:
        metrics = item["metrics"]
        sections_out = [
            schemas.TimetableSection(
                course_code=s.course_code,
                section=s.section,
                title=s.title,
                instructor=s.instructor,
                credits=s.credits,
                ects=s.ects,
                slots=s.slots,
            )
            for s in item["sections"]
        ]
        result_combinations.append(
            schemas.TimetableCombination(
                score=metrics["score"],
                total_credits=metrics["total_credits"],
                total_ects=metrics["total_ects"],
                campus_days=metrics["campus_days"],
                total_gap_hours=metrics["total_gap_hours"],
                sections=sections_out,
            )
        )
    return result_combinations


def _normalize_course_list(raw_codes: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in raw_codes:
        norm = " ".join((raw or "").split()).upper()
        if norm and norm not in seen:
            seen.add(norm)
            normalized.append(norm)
    return normalized


def _empty_opt_response(term_id: str, message: str) -> schemas.ScheduleOptimizationResponse:
    return schemas.ScheduleOptimizationResponse(
        term_id=term_id,
        success=False,
        total_combinations_found=0,
        combinations=[],
        message=message,
    )


def solve_schedule_csp(
    db: Session,
    request: schemas.ScheduleOptimizationRequest,
) -> schemas.ScheduleOptimizationResponse:
    required_course_keys = _normalize_course_list(request.target_courses)
    required_set = set(required_course_keys)
    elective_pool = [c for c in _normalize_course_list(request.candidate_electives) if c not in required_set]

    if not required_course_keys and request.num_electives_needed == 0:
        return _empty_opt_response(request.term_id, "At least one required course or elective must be specified.")

    all_codes = required_course_keys + elective_pool
    sections_by_course = fetch_course_sections(db, request.term_id, all_codes)

    missing_required = [c for c in required_course_keys if not sections_by_course.get(c)]
    if missing_required:
        return _empty_opt_response(
            request.term_id, f"Courses not offered in term {request.term_id}: {', '.join(missing_required)}"
        )

    filtered_by_course = _filter_sections_by_constraints(sections_by_course, request)
    pruned_required = [c for c in required_course_keys if not filtered_by_course.get(c)]
    if pruned_required:
        return _empty_opt_response(
            request.term_id,
            f"No sections available for {', '.join(pruned_required)} matching your hour and day constraints.",
        )

    elective_course_keys = [e for e in elective_pool if filtered_by_course.get(e)]
    if request.num_electives_needed > len(elective_course_keys):
        return _empty_opt_response(
            request.term_id,
            f"Requested {request.num_electives_needed} elective(s), but only {len(elective_course_keys)} candidate(s) match constraints.",
        )

    candidate_group_sets = _build_candidate_groups(
        required_course_keys, elective_course_keys, request.num_electives_needed
    )

    valid_combinations = _run_csp_backtrack(candidate_group_sets, filtered_by_course, request.max_campus_days)
    valid_combinations.sort(
        key=lambda x: (-x["metrics"]["score"], x["metrics"]["total_gap_hours"], len(x["metrics"]["campus_days"]))
    )

    result_combinations = _serialize_combinations(valid_combinations[: request.max_results])
    return schemas.ScheduleOptimizationResponse(
        term_id=request.term_id,
        success=len(result_combinations) > 0,
        total_combinations_found=len(valid_combinations),
        combinations=result_combinations,
        message=(
            f"Found {len(valid_combinations)} conflict-free schedule combinations."
            if valid_combinations
            else "No conflict-free schedule combination could be resolved for the chosen constraints."
        ),
    )
