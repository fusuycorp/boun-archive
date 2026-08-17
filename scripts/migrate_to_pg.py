import pandas as pd
import sqlite3
import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pathutil import add_import_paths, ROOT_DIR, SCRIPT_DIR

add_import_paths()

from app.database import Base
from app.models import Term, Department, Instructor, Room, Course, CourseSlot

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

def clean_int(value):
    if pd.isna(value):
        return None
    value_str = str(value).strip()
    return int(value_str) if value_str.isdigit() else None

def migrate():
    print("Starting migration from SQLite to PostgreSQL...")
    
    # 1. Setup Connections
    schedules_db_path = find_data_file('schedules.db')
    sqlite_conn = sqlite3.connect(schedules_db_path)
    pg_url = os.getenv("DATABASE_URL")
    engine = create_engine(pg_url)
    
    # Idempotency check: Skip if courses table exists and contains records
    inspector = inspect(engine)
    if inspector.has_table("courses"):
        try:
            with engine.connect() as conn:
                res = conn.execute(text("SELECT COUNT(*) FROM courses")).scalar()
                if res > 0:
                    print("PostgreSQL already contains migrated course data. Skipping SQLite migration.")
                    return
        except Exception as e:
            print(f"Error checking course table status (table may be corrupted): {e}. Proceeding with fresh migration.")

    Session = sessionmaker(bind=engine)
    session = Session()

    # 2. Create Schema
    print("Dropping existing tables...")
    Base.metadata.drop_all(engine)
    print("Creating tables in PostgreSQL...")
    Base.metadata.create_all(engine)

    # 3. Load Departments (from CSV)
    print("Migrating Departments...")
    depts_csv_path = find_data_file('departments.csv')
    depts_df = pd.read_csv(depts_csv_path)
    depts_df = depts_df.drop_duplicates(subset=['kisaadi'], keep='first')
    for _, row in depts_df.iterrows():
        dept = Department(kisaadi=row['kisaadi'], bolum=row['bolum'])
        session.merge(dept)
    session.commit()

    # 4. Load Terms
    print("Migrating Terms...")
    courses_raw = pd.read_sql_query("SELECT DISTINCT term FROM courses", sqlite_conn)
    for term_id in courses_raw['term']:
        if '-' in term_id:
            year, sem = term_id.split('-')
            term = Term(id=term_id, academic_year=year, semester_num=int(sem))
            session.merge(term)
    session.commit()

    # 5. Load Instructors
    print("Migrating Instructors...")
    all_inst = pd.read_sql_query("SELECT DISTINCT instructor FROM courses", sqlite_conn)
    inst_set = set(all_inst['instructor'].dropna().unique())
    # Add instructors from slots too
    all_inst_slots = pd.read_sql_query("SELECT DISTINCT instructor FROM course_slots", sqlite_conn)
    inst_set.update(all_inst_slots['instructor'].dropna().unique())
    
    for name in inst_set:
        inst = Instructor(full_name=name)
        session.add(inst)
    session.commit()

    # 6. Load Rooms
    print("Migrating Rooms...")
    all_rooms = pd.read_sql_query("SELECT DISTINCT room FROM course_slots", sqlite_conn)
    for name in all_rooms['room'].dropna().unique():
        if name and name.strip():
            room = Room(name=name.strip())
            session.add(room)
    session.commit()

    # 7. Migrate Courses (Bulk)
    print("Migrating Courses (this may take a moment)...")
    courses_df = pd.read_sql_query("SELECT * FROM courses", sqlite_conn)
    
    # Map instructor names to IDs for efficiency
    inst_map = {i.full_name: i.id for i in session.query(Instructor).all()}
    
    # Normalize course codes
    courses_df['course_code'] = courses_df['course_code'].str.replace(r'\s+', ' ', regex=True).str.strip()
    
    course_records = []
    for _, row in courses_df.iterrows():
        course_records.append({
            "id": int(row['id']),
            "term_id": clean_value(row['term']),
            "dept_kisaadi": clean_value(row['department']),
            "course_code": clean_value(row['course_code']),
            "section": clean_string(row['section']),
            "title": clean_value(row['course_name']),
            "instructor_id": inst_map.get(row['instructor']) if pd.notna(row['instructor']) else None,
            "credits": clean_int(row['credits']),
            "ects": clean_int(row['ects']),
            "delivery_method": clean_value(row['delivery_method']),
        })
    
    session.bulk_insert_mappings(Course, course_records)
    session.execute(text("SELECT setval(pg_get_serial_sequence('courses','id'), COALESCE((SELECT MAX(id) FROM courses), 1))"))
    session.commit()

    # 8. Migrate Slots
    print("Migrating Course Slots...")
    slots_df = pd.read_sql_query("SELECT * FROM course_slots", sqlite_conn)
    room_map = {r.name: r.id for r in session.query(Room).all()}
    
    slot_records = []
    for _, row in slots_df.iterrows():
        room_name = clean_string(row['room'])
        slot_records.append({
            "course_id": int(row['course_id']),
            "day_code": clean_string(row['day']),
            "slot_hour": clean_int(row['hour']),
            "slot_title": clean_value(row['slot_title']),
            "room_id": room_map.get(room_name) if room_name else None,
        })
    
    session.bulk_insert_mappings(CourseSlot, slot_records)
    session.commit()

    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
