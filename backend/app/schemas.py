from pydantic import BaseModel
from typing import List, Optional, Dict

class TermBase(BaseModel):
    id: str
    academic_year: str
    semester_num: int

class Term(TermBase):
    class Config:
        from_attributes = True

class DepartmentBase(BaseModel):
    kisaadi: str
    bolum: str

class Department(DepartmentBase):
    class Config:
        from_attributes = True

class InstructorBase(BaseModel):
    full_name: str

class Instructor(InstructorBase):
    id: int
    class Config:
        from_attributes = True

class RoomBase(BaseModel):
    name: str
    building: Optional[str] = None
    capacity: Optional[int] = None

class Room(RoomBase):
    id: int
    class Config:
        from_attributes = True

class CourseSlotBase(BaseModel):
    day_code: Optional[str] = None
    slot_hour: Optional[int] = None
    slot_title: Optional[str] = None
    room_id: Optional[int] = None

class CourseSlot(CourseSlotBase):
    id: int
    room_name: Optional[str] = None
    class Config:
        from_attributes = True

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
    class Config:
        from_attributes = True

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
    class Config:
        from_attributes = True

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
    class Config:
        from_attributes = True

class SyncStateBase(BaseModel):
    feed_name: str
    last_cursor: Optional[str] = None

class SyncState(SyncStateBase):
    class Config:
        from_attributes = True

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
    latest_scrape_time: Optional[str] = None
    upstream_scrape_time: Optional[str] = None
    last_sync_time: Optional[str] = None
    is_stale: bool = False
    upstream_run: Optional[UpstreamRunInfo] = None
    feeds: Dict[str, FeedState] = {}
