from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    building: str | None = None
    capacity: int | None = None

class Room(RoomBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class CourseSlotBase(BaseModel):
    day_code: str | None = None
    slot_hour: int | None = None
    slot_title: str | None = None
    room_id: int | None = None

class CourseSlot(CourseSlotBase):
    id: int
    course_id: int | None = None
    room_name: str | None = None
    room: Room | None = None
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
    section: str | None = None
    title: str | None = None
    instructor_id: int | None = None
    credits: int | None = None
    ects: int | None = None
    delivery_method: str | None = None
    desc_url: str | None = None
    syllabus_url: str | None = None
    has_syllabus: bool = False

class Course(CourseBase):
    id: int
    slots: list[CourseSlot] = []
    instructor_name: str | None = None
    instructor: Instructor | None = None
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def resolve_instructor_name(self):
        if not self.instructor_name and self.instructor:
            self.instructor_name = self.instructor.full_name
        return self

class QuotaSnapshotBase(BaseModel):
    term_id: str
    course_code: str
    section: str | None = None
    department: str | None = None
    status: str | None = None
    quota: str | None = None
    current: str | None = None
    quota_numeric: int | None = None
    current_numeric: int | None = None
    is_consent: bool = False
    is_unlimited: bool = False
    available: int | None = None
    captured_at: str

class QuotaSnapshot(QuotaSnapshotBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class CourseChangeBase(BaseModel):
    change_type: str
    term_id: str
    dept_kisaadi: str | None = None
    course_code: str
    section: str | None = None
    timestamp: str
    old_value: str | None = None
    new_value: str | None = None
    details: str | None = None

class CourseChange(CourseChangeBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class SyncStateBase(BaseModel):
    feed_name: str
    last_cursor: str | None = None

class SyncState(SyncStateBase):
    model_config = ConfigDict(from_attributes=True)

class FeedState(BaseModel):
    last_cursor: str | None = None
    updated_at: str | None = None

class UpstreamRunInfo(BaseModel):
    run_id: str | None = None
    term: str | None = None
    status: str | None = None
    total_courses: int | None = None
    changes_detected: int | None = None
    completed_at: str | None = None
    started_at: str | None = None

class SystemStatusResponse(BaseModel):
    status: str = "healthy"
    last_scraped_at: str | None = None
    last_sync_at: str | None = None
    latest_scrape_time: str | None = None
    upstream_scrape_time: str | None = None
    last_sync_time: str | None = None
    is_stale: bool = False
    upstream_run: UpstreamRunInfo | None = None
    feeds: dict[str, FeedState] = {}

class ScheduleOptimizationRequest(BaseModel):
    term_id: str
    target_courses: list[str] = Field(default=[], max_length=20)
    candidate_electives: list[str] = Field(default=[], max_length=30)
    num_electives_needed: int = Field(default=0, ge=0, le=10)
    avoid_days: list[str] = Field(default=[], max_length=7)
    min_hour: int = Field(default=1, ge=1, le=14)
    max_hour: int = Field(default=14, ge=1, le=14)
    max_campus_days: int | None = Field(default=None, ge=1, le=7)
    max_results: int = Field(default=5, ge=1, le=50)

    @model_validator(mode="after")
    def validate_hour_bounds(self):
        if self.min_hour > self.max_hour:
            raise ValueError("min_hour must be less than or equal to max_hour")
        return self

class TimetableSection(BaseModel):
    course_code: str
    section: str
    title: str | None = None
    instructor: str | None = None
    credits: int | None = None
    ects: int | None = None
    slots: list[dict[str, Any]] = []

class TimetableCombination(BaseModel):
    score: float
    total_credits: int
    total_ects: int
    campus_days: list[str]
    total_gap_hours: int
    sections: list[TimetableSection]

class ScheduleOptimizationResponse(BaseModel):
    term_id: str
    success: bool
    total_combinations_found: int
    combinations: list[TimetableCombination]
    message: str | None = None


class CourseCatalogResponse(BaseModel):
    course_code: str
    found: bool = False
    title: str | None = None
    en_url: str | None = None
    tr_url: str | None = None
    en_text: str | None = None
    tr_text: str | None = None
    canonical_text: str | None = None
    updated_at: str | None = None


class CourseSyllabusResponse(BaseModel):
    course_id: int
    term_id: str
    course_code: str
    section: str | None = None
    has_syllabus: bool = False
    syllabus_url: str | None = None
    desc_url: str | None = None
    syllabus_text: str = ""

