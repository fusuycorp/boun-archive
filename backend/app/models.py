from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Term(Base):
    __tablename__ = "terms"
    id = Column(String(15), primary_key=True)
    academic_year = Column(String(9), nullable=False)
    semester_num = Column(Integer, nullable=False)
    courses = relationship("Course", back_populates="term")

class Department(Base):
    __tablename__ = "departments"
    kisaadi = Column(String(10), primary_key=True)
    bolum = Column(String(100), nullable=False)
    courses = relationship("Course", back_populates="department")

class Instructor(Base):
    __tablename__ = "instructors"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), unique=True, nullable=False, index=True)
    courses = relationship("Course", back_populates="instructor")

class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    building = Column(String(50))
    capacity = Column(Integer)
    slots = relationship("CourseSlot", back_populates="room")

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    term_id = Column(String(15), ForeignKey("terms.id"), index=True)
    dept_kisaadi = Column(String(10), ForeignKey("departments.kisaadi"), index=True)
    course_code = Column(String(20), nullable=False, index=True)
    section = Column(String(5))
    title = Column(String(255))
    instructor_id = Column(Integer, ForeignKey("instructors.id"), index=True)
    credits = Column(Integer)
    ects = Column(Integer)
    delivery_method = Column(String(50))

    term = relationship("Term", back_populates="courses")
    department = relationship("Department", back_populates="courses")
    instructor = relationship("Instructor", back_populates="courses")
    slots = relationship("CourseSlot", back_populates="course")

class CourseSlot(Base):
    __tablename__ = "course_slots"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), index=True)
    day_code = Column(String(10), index=True)
    slot_hour = Column(Integer, index=True)
    slot_title = Column(String(255))
    room_id = Column(Integer, ForeignKey("rooms.id"), index=True)

    course = relationship("Course", back_populates="slots")
    room = relationship("Room", back_populates="slots")

    @property
    def room_name(self) -> str:
        return self.room.name if self.room else "N/A"

