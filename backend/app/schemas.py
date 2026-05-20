from pydantic import BaseModel
from typing import List, Optional

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
    day_code: str
    slot_hour: int
    room_id: int

class CourseSlot(CourseSlotBase):
    id: int
    class Config:
        from_attributes = True

class CourseBase(BaseModel):
    term_id: str
    dept_kisaadi: str
    course_code: str
    section: Optional[str] = None
    title: Optional[str] = None
    instructor_id: int
    credits: Optional[int] = None
    ects: Optional[int] = None
    delivery_method: Optional[str] = None

class Course(CourseBase):
    id: int
    slots: List[CourseSlot] = []
    class Config:
        from_attributes = True
