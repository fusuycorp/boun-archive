from typing import List, Dict, Any, Optional, Set, Tuple
from itertools import combinations
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
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
        credits: Optional[int],
        ects: Optional[int],
        slots: List[Dict[str, Any]]
    ):
        self.course_id = course_id
        self.course_code = course_code
        self.section = section
        self.title = title
        self.instructor = instructor
        self.credits = credits or 0
        self.ects = ects or 0
        self.slots = slots
        self.occupied_slots: Set[Tuple[str, int]] = {
            (s["day_code"], int(s["slot_hour"]))
            for s in slots
            if s.get("day_code") and s.get("slot_hour") is not None
        }

    def has_conflict(self, other: "SectionSlotData") -> bool:
        return bool(self.occupied_slots.intersection(other.occupied_slots))


def calculate_schedule_metrics(selected_sections: List[SectionSlotData]) -> Dict[str, Any]:
    day_hours: Dict[str, List[int]] = {}
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
    course_codes: List[str]
) -> Dict[str, List[SectionSlotData]]:
    results: Dict[str, List[SectionSlotData]] = {}
    
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


def solve_schedule_csp(
    db: Session,
    request: schemas.ScheduleOptimizationRequest
) -> schemas.ScheduleOptimizationResponse:
    all_codes = list(set([c.upper() for c in request.target_courses] + [e.upper() for e in request.candidate_electives]))
    sections_by_course = fetch_course_sections(db, request.term_id, all_codes)

    missing_required = [c for c in request.target_courses if c.upper() not in sections_by_course or not sections_by_course[c.upper()]]
    if missing_required:
        return schemas.ScheduleOptimizationResponse(
            term_id=request.term_id,
            success=False,
            total_combinations_found=0,
            combinations=[],
            message=f"Courses not offered in term {request.term_id}: {', '.join(missing_required)}"
        )

    avoid_days_set = set(request.avoid_days)
    filtered_by_course: Dict[str, List[SectionSlotData]] = {}

    for code, sec_list in sections_by_course.items():
        valid_secs = []
        for sec in sec_list:
            hours = [h for _, h in sec.occupied_slots]
            days = [d for d, _ in sec.occupied_slots]
            
            if hours and (min(hours) < request.min_hour or max(hours) > request.max_hour):
                continue
            if avoid_days_set and any(d in avoid_days_set for d in days):
                continue
            valid_secs.append(sec)

        filtered_by_course[code] = valid_secs

    pruned_required = [c for c in request.target_courses if not filtered_by_course.get(c.upper())]
    if pruned_required:
        return schemas.ScheduleOptimizationResponse(
            term_id=request.term_id,
            success=False,
            total_combinations_found=0,
            combinations=[],
            message=f"No sections available for {', '.join(pruned_required)} matching your hour and day constraints."
        )

    required_course_keys = [c.upper() for c in request.target_courses]
    elective_course_keys = [e.upper() for e in request.candidate_electives if filtered_by_course.get(e.upper())]
    num_electives = min(request.num_electives_needed, len(elective_course_keys))

    candidate_group_sets: List[List[str]] = []
    if num_electives > 0:
        for elect_comb in combinations(elective_course_keys, num_electives):
            candidate_group_sets.append(required_course_keys + list(elect_comb))
    else:
        candidate_group_sets.append(required_course_keys)

    valid_combinations: List[Dict[str, Any]] = []

    def backtrack(
        course_list: List[str],
        index: int,
        current_assignment: List[SectionSlotData],
        current_occupied: Set[Tuple[str, int]]
    ):
        if index == len(course_list):
            metrics = calculate_schedule_metrics(current_assignment)
            if request.max_campus_days and len(metrics["campus_days"]) > request.max_campus_days:
                return
            valid_combinations.append({
                "sections": list(current_assignment),
                "metrics": metrics
            })
            return

        current_code = course_list[index]
        available_sections = filtered_by_course.get(current_code, [])

        for sec in available_sections:
            if not sec.occupied_slots.intersection(current_occupied):
                backtrack(
                    course_list,
                    index + 1,
                    current_assignment + [sec],
                    current_occupied.union(sec.occupied_slots)
                )

    for group_set in candidate_group_sets:
        backtrack(group_set, 0, [], set())

    valid_combinations.sort(
        key=lambda x: (-x["metrics"]["score"], x["metrics"]["total_gap_hours"], len(x["metrics"]["campus_days"]))
    )

    top_results = valid_combinations[:request.max_results]
    
    result_combinations = []
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
                slots=s.slots
            ) for s in item["sections"]
        ]
        result_combinations.append(
            schemas.TimetableCombination(
                score=metrics["score"],
                total_credits=metrics["total_credits"],
                total_ects=metrics["total_ects"],
                campus_days=metrics["campus_days"],
                total_gap_hours=metrics["total_gap_hours"],
                sections=sections_out
            )
        )

    return schemas.ScheduleOptimizationResponse(
        term_id=request.term_id,
        success=len(result_combinations) > 0,
        total_combinations_found=len(valid_combinations),
        combinations=result_combinations,
        message=f"Found {len(valid_combinations)} conflict-free schedule combinations." if valid_combinations else "No conflict-free schedule combination could be resolved for the chosen constraints."
    )
