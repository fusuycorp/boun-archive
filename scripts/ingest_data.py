import pandas as pd
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

def ingest():
    print("Starting ingestion process...")
    
    # 1. Connect to Source (SQLite)
    sqlite_conn = sqlite3.connect('schedules.db')
    
    # 2. Load Departments
    print("Loading departments...")
    depts_df = pd.read_csv('departments.csv')
    # Deduplicate by kisaadi, keeping the first (usually most general) name
    depts_df = depts_df.drop_duplicates(subset=['kisaadi'], keep='first')
    
    # 3. Load Courses and Slots from SQLite
    print("Reading courses and slots from SQLite...")
    courses_raw = pd.read_sql_query("SELECT * FROM courses", sqlite_conn)
    slots_raw = pd.read_sql_query("SELECT * FROM course_slots", sqlite_conn)
    
    # 4. Extract Unique Entities
    print("Extracting unique entities (Instructors, Rooms, Terms)...")
    
    # Instructors
    all_instructors = pd.concat([courses_raw['instructor'], slots_raw['instructor']]).dropna().unique()
    instructors_df = pd.DataFrame({'full_name': all_instructors})
    
    # Rooms
    all_rooms = slots_raw['room'].dropna().unique()
    rooms_df = pd.DataFrame({'name': all_rooms})
    
    # Terms
    all_terms = courses_raw['term'].unique()
    terms_list = []
    for term_id in all_terms:
        # e.g., 2016/2017-2
        if '-' in term_id:
            year, sem = term_id.split('-')
            terms_list.append({'id': term_id, 'academic_year': year, 'semester_num': int(sem)})
    terms_df = pd.DataFrame(terms_list)
    
    # 5. Transform Data for courses and slots
    print("Transforming course data...")
    
    # Normalize course_code (e.g., 'TR  521' -> 'TR 521')
    courses_raw['course_code'] = courses_raw['course_code'].str.replace(r'\s+', ' ', regex=True).str.strip()
    
    # Map foreign keys (this would be easier with SQL joins in the target DB, 
    # but we can do some mapping here if needed before bulk load)
    
    print("\nSummary of data to be ingested:")
    print(f"Terms: {len(terms_df)}")
    print(f"Departments: {len(depts_df)}")
    print(f"Instructors: {len(instructors_df)}")
    print(f"Rooms: {len(rooms_df)}")
    print(f"Courses: {len(courses_raw)}")
    print(f"Course Slots: {len(slots_raw)}")

    # In a real scenario, we'd use sqlalchemy/psycopg2 to load into Postgres here.
    # For now, we've validated the extraction logic.

if __name__ == "__main__":
    ingest()
