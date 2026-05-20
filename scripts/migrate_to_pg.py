import pandas as pd
import sqlite3
import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add backend to path to import app modules when running from root or in container
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from app.database import Base
from app.models import Term, Department, Instructor, Room, Course, CourseSlot

load_dotenv()

def migrate():
    print("Starting migration from SQLite to PostgreSQL...")
    
    # 1. Setup Connections
    sqlite_conn = sqlite3.connect('schedules.db')
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
    depts_df = pd.read_csv('departments.csv')
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
    
    # Convert to objects
    course_objects = []
    for _, row in courses_df.iterrows():
        course = Course(
            id=row['id'],
            term_id=row['term'],
            dept_kisaadi=row['department'],
            course_code=row['course_code'],
            section=row['section'],
            title=row['course_name'],
            instructor_id=inst_map.get(row['instructor']),
            credits=int(row['credits']) if row['credits'] and str(row['credits']).isdigit() else None,
            ects=int(row['ects']) if row['ects'] and str(row['ects']).isdigit() else None,
            delivery_method=row['delivery_method']
        )
        course_objects.append(course)
    
    session.bulk_save_objects(course_objects)
    session.commit()

    # 8. Migrate Slots
    print("Migrating Course Slots...")
    slots_df = pd.read_sql_query("SELECT * FROM course_slots", sqlite_conn)
    room_map = {r.name: r.id for r in session.query(Room).all()}
    
    slot_objects = []
    for _, row in slots_df.iterrows():
        # Map hour to int if possible
        try:
            hour_val = int(row['hour']) if row['hour'] and str(row['hour']).isdigit() else None
        except:
            hour_val = None
            
        slot = CourseSlot(
            course_id=row['course_id'],
            day_code=row['day'],
            slot_hour=hour_val,
            slot_title=row['slot_title'],
            room_id=room_map.get(row['room'].strip()) if row['room'] else None
        )
        slot_objects.append(slot)
    
    session.bulk_save_objects(slot_objects)
    session.commit()

    print("Migration completed successfully!")

if __name__ == "__main__":
    # We need to be in the backend directory or add it to path
    import sys
    sys.path.append(os.path.join(os.getcwd(), 'backend'))
    migrate()
