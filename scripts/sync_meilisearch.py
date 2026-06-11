import os
import meilisearch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import sys

# Add backend to path to import models
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from app.models import Course, Term, Department, Instructor

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
    
    # 2. Fetch data from PG with joins
    print("Fetching courses from PostgreSQL...")
    courses = session.query(Course).join(Term).join(Department).outerjoin(Instructor).all()
    
    print(f"Preparing {len(courses)} documents...")
    documents = []
    for c in courses:
        doc = {
            'id': c.id,
            'course_code': c.course_code,
            'title': c.title,
            'section': c.section,
            'term': c.term_id,
            'department': c.department.bolum,
            'dept_code': c.dept_kisaadi,
            'instructor': c.instructor.full_name if c.instructor else "TBA",
            'credits': c.credits,
            'ects': c.ects,
            'delivery_method': c.delivery_method
        }
        documents.append(doc)
    
    # 3. Push to Meilisearch in chunks
    print("Pushing to Meilisearch...")
    chunk_size = 1000
    for i in range(0, len(documents), chunk_size):
        chunk = documents[i:i + chunk_size]
        index.add_documents(chunk)
        print(f"Pushed chunk {i//chunk_size + 1}")
    
    # 4. Configure Index (Facets/Searchable)
    print("Configuring index...")
    index.update_settings({
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
    
    print("Meilisearch sync completed!")

if __name__ == "__main__":
    sync_meilisearch()
