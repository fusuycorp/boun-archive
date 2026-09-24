from pydantic import BaseModel, ConfigDict, model_validator
from typing import List, Optional, Dict, Any

class TermBase(BaseModel):
    id: str
    academic_year: str
    semester_num: int

class Term(TermBase):
    model_config = ConfigDict(from_attributes=True)

class DepartmentBase(BaseModel):
    kisaadi: str
    bolum: str

class Department(DepartmentBase):
    model_config = ConfigDict(from_attributes=True)

class InstructorBase(BaseModel):
    full_name: str

class Instructor(InstructorBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class RoomBase(BaseModel):
    name: str
    building: Optional[str] = None
    capacity: Optional[int] = None

class Room(RoomBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class CourseSlotBase(BaseModel):
    day_code: Optional[str] = None
    slot_hour: Optional[int] = None
    slot_title: Optional[str] = None
    room_id: Optional[int] = None

class CourseSlot(CourseSlotBase):
    id: int
    room_name: Optional[str] = None
    room: Optional[Room] = None
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def resolve_room_name(self):
        if (not self.room_name or self.room_name == "N/A") and self.room:
            self.room_name = self.room.name
        return self

class CourseBase(BaseModel):
    term_id: str
    dept_kisaadi: str
    course_code: str
    section: Optional[str] = None
    title: Optional[str] = None
    instructor_id: Optional[int] = None
    credits: Optional[int] = None
    ects: Optional[int] = None
    delivery_method: Optional[str] = None

class Course(CourseBase):
    id: int
    slots: List[CourseSlot] = []
    instructor_name: Optional[str] = None
    instructor: Optional[Instructor] = None
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def resolve_instructor_name(self):
        if not self.instructor_name and self.instructor:
            self.instructor_name = self.instructor.full_name
        return self

class QuotaSnapshotBase(BaseModel):
    term_id: str
    course_code: str
    section: Optional[str] = None
    department: Optional[str] = None
    status: Optional[str] = None
    quota: Optional[str] = None
    current: Optional[str] = None
    quota_numeric: Optional[int] = None
    current_numeric: Optional[int] = None
    is_consent: bool = False
    is_unlimited: bool = False
    available: Optional[int] = None
    captured_at: str

class QuotaSnapshot(QuotaSnapshotBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class CourseChangeBase(BaseModel):
    change_type: str
    term_id: str
    dept_kisaadi: Optional[str] = None
    course_code: str
    section: Optional[str] = None
    timestamp: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    details: Optional[str] = None

class CourseChange(CourseChangeBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class SyncStateBase(BaseModel):
    feed_name: str
    last_cursor: Optional[str] = None

class SyncState(SyncStateBase):
    model_config = ConfigDict(from_attributes=True)

class FeedState(BaseModel):
    last_cursor: Optional[str] = None
    updated_at: Optional[str] = None

class UpstreamRunInfo(BaseModel):
    run_id: Optional[str] = None
    term: Optional[str] = None
    status: Optional[str] = None
    total_courses: Optional[int] = None
    changes_detected: Optional[int] = None
    completed_at: Optional[str] = None
    started_at: Optional[str] = None

class SystemStatusResponse(BaseModel):
    status: str = "healthy"
    last_scraped_at: Optional[str] = None
    last_sync_at: Optional[str] = None
    latest_scrape_time: Optional[str] = None
    upstream_scrape_time: Optional[str] = None
    last_sync_time: Optional[str] = None
    is_stale: bool = False
    upstream_run: Optional[UpstreamRunInfo] = None
    feeds: Dict[str, FeedState] = {}

class ScheduleOptimizationRequest(BaseModel):
    term_id: str
    target_courses: List[str]
    candidate_electives: List[str] = []
    num_electives_needed: int = 0
    avoid_days: List[str] = []
    min_hour: int = 1
    max_hour: int = 14
    max_campus_days: Optional[int] = None
    max_results: int = 5

class TimetableSection(BaseModel):
    course_code: str
    section: str
    title: Optional[str] = None
    instructor: Optional[str] = None
    credits: Optional[int] = None
    ects: Optional[int] = None
    slots: List[Dict[str, Any]] = []

class TimetableCombination(BaseModel):
    score: float
    total_credits: int
    total_ects: int
    campus_days: List[str]
    total_gap_hours: int
    sections: List[TimetableSection]

class ScheduleOptimizationResponse(BaseModel):
    term_id: str
    success: bool
    total_combinations_found: int
    combinations: List[TimetableCombination]
    message: Optional[str] = None

