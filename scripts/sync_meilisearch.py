import os
import meilisearch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from dotenv import load_dotenv
import sys

# Add backend to path to import models
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from app.models import Course, Term, Department, Instructor, CourseSlot, Room

load_dotenv()

def sync_meilisearch():
    print("Starting Meilisearch sync...")
    
    # 1. Setup Connections
    pg_url = os.getenv("DATABASE_URL")
    engine = create_engine(pg_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    client = meilisearch.Client(
        os.getenv("MEILI_URL"), 
        os.getenv("MEILI_MASTER_KEY")
    )
    
    index = client.index('courses')
    
    # 2. Fetch data from PG with joins, including slots and rooms
    print("Fetching courses from PostgreSQL...")
    query = session.query(Course).options(
        joinedload(Course.term),
        joinedload(Course.department),
        joinedload(Course.instructor),
        joinedload(Course.slots).joinedload(CourseSlot.room)
    )
    
    print("Preparing and pushing documents to Meilisearch in chunks...")
    chunk_size = 1000
    chunk_count = 0
    documents = []
    
    for c in query.yield_per(chunk_size):
        slots_data = []
        for s in c.slots:
            slots_data.append({
                'day_code': s.day_code,
                'slot_hour': s.slot_hour,
                'slot_title': s.slot_title,
                'room_name': s.room.name if s.room else None
            })

        doc = {
            'id': c.id,
            'course_code': c.course_code,
            'title': c.title,
            'section': c.section,
            'term': c.term_id,
            'department': c.department.bolum if c.department else None,
            'dept_code': c.dept_kisaadi,
            'instructor': c.instructor.full_name if c.instructor else "TBA",
            'credits': c.credits,
            'ects': c.ects,
            'delivery_method': c.delivery_method,
            'slots': slots_data
        }
        documents.append(doc)
        
        if len(documents) >= chunk_size:
            task = index.add_documents(documents)
            client.wait_for_task(task.task_uid)
            chunk_count += 1
            print(f"Pushed chunk {chunk_count}")
            documents = []
            
    if documents:
        task = index.add_documents(documents)
        client.wait_for_task(task.task_uid)
        chunk_count += 1
        print(f"Pushed final chunk {chunk_count}")
    
    # 4. Configure Index (Facets/Searchable)
    print("Configuring index...")
    task = index.update_settings({
        'filterableAttributes': [
            'term', 'dept_code', 'department', 'instructor', 'delivery_method'
        ],
        'searchableAttributes': [
            'course_code', 'title', 'instructor', 'department'
        ],
        'faceting': {
            'maxValuesPerFacet': 1000
        },
        'sortableAttributes': ['term', 'course_code', 'title', 'instructor', 'credits', 'ects']
    })
    client.wait_for_task(task.task_uid)
    
    print("Meilisearch sync completed!")

if __name__ == "__main__":
    sync_meilisearch()
