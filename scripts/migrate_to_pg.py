import os
import sqlite3
import sys

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pathutil import ROOT_DIR, SCRIPT_DIR, add_import_paths

add_import_paths()

from app.database import Base
from app.models import Course, CourseSlot, Department, Instructor, Room, Term
from app.sync import clean_int

load_dotenv()


def find_data_file(filename: str) -> str:
    candidates = [
        os.path.join(os.getcwd(), filename),
        os.path.join(ROOT_DIR, filename),
        os.path.join(SCRIPT_DIR, filename),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    raise FileNotFoundError(f"{filename} not found in any of: {candidates}")


def clean_value(value):
    return None if pd.isna(value) else value


def clean_string(value):
    if pd.isna(value):
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _already_migrated(engine) -> bool:
    inspector = inspect(engine)
    if not inspector.has_table("courses"):
        return False
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT COUNT(*) FROM courses")).scalar()
            if res > 0:
                print("PostgreSQL already contains migrated course data. Skipping SQLite migration.")
                return True
    except Exception as e:
        print(f"Error checking course table status (table may be corrupted): {e}. Proceeding with fresh migration.")
    return False


def _migrate_terms(session, sqlite_conn) -> None:
    print("Migrating Terms...")
    courses_raw = pd.read_sql_query("SELECT DISTINCT term FROM courses", sqlite_conn)
    for term_id in courses_raw["term"]:
        if term_id and ("-" in term_id or "/" in term_id):
            parts = term_id.rsplit("-", 1) if "-" in term_id else term_id.rsplit("/", 1)
            year = parts[0]
            sem = clean_int(parts[1]) if len(parts) > 1 else 1
            session.merge(Term(id=term_id, academic_year=year, semester_num=sem or 1))
    session.commit()


def _migrate_instructors_and_rooms(session, sqlite_conn) -> None:
    print("Migrating Instructors...")
    all_inst = pd.read_sql_query("SELECT DISTINCT instructor FROM courses", sqlite_conn)
    inst_set = set(all_inst["instructor"].dropna().unique())
    all_inst_slots = pd.read_sql_query("SELECT DISTINCT instructor FROM course_slots", sqlite_conn)
    inst_set.update(all_inst_slots["instructor"].dropna().unique())
    for name in inst_set:
        session.add(Instructor(full_name=name))
    session.commit()

    print("Migrating Rooms...")
    all_rooms = pd.read_sql_query("SELECT DISTINCT room FROM course_slots", sqlite_conn)
    for name in all_rooms["room"].dropna().unique():
        if name and name.strip():
            session.add(Room(name=name.strip()))
    session.commit()


def _migrate_courses_and_slots(session, sqlite_conn) -> None:
    print("Migrating Courses (this may take a moment)...")
    courses_df = pd.read_sql_query("SELECT * FROM courses", sqlite_conn)
    inst_map = {i.full_name: i.id for i in session.query(Instructor).all()}
    courses_df["course_code"] = courses_df["course_code"].str.replace(r"\s+", " ", regex=True).str.strip()

    course_records = [
        {
            "id": int(row["id"]),
            "term_id": clean_value(row["term"]),
            "dept_kisaadi": clean_value(row["department"]),
            "course_code": clean_value(row["course_code"]),
            "section": clean_string(row["section"]),
            "title": clean_value(row["course_name"]),
            "instructor_id": inst_map.get(row["instructor"]) if pd.notna(row["instructor"]) else None,
            "credits": clean_int(row["credits"]),
            "ects": clean_int(row["ects"]),
            "delivery_method": clean_value(row["delivery_method"]),
        }
        for _, row in courses_df.iterrows()
    ]
    session.bulk_insert_mappings(Course, course_records)
    session.execute(
        text("SELECT setval(pg_get_serial_sequence('courses','id'), COALESCE((SELECT MAX(id) FROM courses), 1))")
    )
    session.commit()

    print("Migrating Course Slots...")
    slots_df = pd.read_sql_query("SELECT * FROM course_slots", sqlite_conn)
    room_map = {r.name: r.id for r in session.query(Room).all()}
    slot_records = []
    for _, row in slots_df.iterrows():
        room_name = clean_string(row["room"])
        slot_records.append(
            {
                "course_id": int(row["course_id"]),
                "day_code": clean_string(row["day"]),
                "slot_hour": clean_int(row["hour"]),
                "slot_title": clean_value(row["slot_title"]),
                "room_id": room_map.get(room_name) if room_name else None,
            }
        )
    session.bulk_insert_mappings(CourseSlot, slot_records)
    session.commit()


def migrate():
    print("Starting migration from SQLite to PostgreSQL...")
    pg_url = os.getenv("DATABASE_URL")
    engine = create_engine(pg_url)
    if _already_migrated(engine):
        return

    sqlite_conn = sqlite3.connect(find_data_file("schedules.db"))
    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    print("Creating tables in PostgreSQL if not exist...")
    Base.metadata.create_all(engine)

    print("Migrating Departments...")
    depts_df = pd.read_csv(find_data_file("departments.csv")).drop_duplicates(subset=["kisaadi"], keep="first")
    for _, row in depts_df.iterrows():
        session.merge(Department(kisaadi=row["kisaadi"], bolum=row["bolum"]))
    session.commit()

    _migrate_terms(session, sqlite_conn)
    _migrate_instructors_and_rooms(session, sqlite_conn)
    _migrate_courses_and_slots(session, sqlite_conn)
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
