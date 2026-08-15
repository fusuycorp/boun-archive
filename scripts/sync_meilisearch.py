import os
import sys
import meilisearch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from dotenv import load_dotenv

# Add candidate paths to sys.path so app modules can always be found
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
cwd = os.getcwd()

for p in [cwd, root_dir, os.path.join(root_dir, 'backend'), os.path.join(cwd, 'backend')]:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

from app.models import Course, Term, Department, Instructor, CourseSlot, Room

load_dotenv()

def sync_meilisearch(force: bool = False):
    print("Starting Meilisearch sync...")
    
    meili_url = os.getenv("MEILI_URL", "http://localhost:7700")
    meili_key = os.getenv("MEILI_MASTER_KEY")
    if not meili_key:
        print("MEILI_MASTER_KEY is not set. Aborting sync.")
        return

    client = meilisearch.Client(meili_url, meili_key)
    index = client.index('courses')
    
    # Idempotency check: Skip if courses index already has documents, unless force=True
    if not force and "--force" not in sys.argv:
        try:
            stats = index.get_stats()
            doc_count = getattr(stats, 'number_of_documents', None)
            if doc_count is None and isinstance(stats, dict):
                doc_count = stats.get('numberOfDocuments', 0)
            if doc_count and doc_count > 0:
                print(f"Meilisearch already contains {doc_count} indexed courses. Skipping sync (pass --force to re-sync).")
                return
        except Exception:
            # Index might not exist yet; continue to create and sync
            pass

    # 1. Setup Database Connection
    pg_url = os.getenv("DATABASE_URL")
    engine = create_engine(pg_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # 2. Configure Index Settings first
    print("Configuring index settings...")
    config_task = index.update_settings({
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
    
    # 3. Fetch data from PG with joins, including slots and rooms
    print("Fetching courses from PostgreSQL...")
    query = session.query(Course).options(
        joinedload(Course.term),
        joinedload(Course.department),
        joinedload(Course.instructor),
        joinedload(Course.slots).joinedload(CourseSlot.room)
    )
    
    print("Preparing and pushing documents to Meilisearch in chunks...")
    chunk_size = 2000
    chunk_count = 0
    documents = []
    last_task = None
    
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
            last_task = index.add_documents(documents)
            chunk_count += 1
            if chunk_count % 10 == 0:
                print(f"Queued chunk {chunk_count}...")
            documents = []
            
    if documents:
        last_task = index.add_documents(documents)
        chunk_count += 1
        print(f"Queued final chunk {chunk_count}")
    
    if last_task:
        print(f"Awaiting indexing completion for task UID {last_task.task_uid}...")
        client.wait_for_task(last_task.task_uid)
        
    print("Meilisearch sync completed!")

if __name__ == "__main__":
    force_sync = "--force" in sys.argv
    sync_meilisearch(force=force_sync)
