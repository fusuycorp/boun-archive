import os
import meilisearch
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

from . import models, schemas, database

app = FastAPI(title="BOUN Archive API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Meilisearch Client
MEILI_CLIENT = meilisearch.Client(
    os.getenv("MEILI_URL", "http://localhost:7700"), 
    os.getenv("MEILI_MASTER_KEY", "masterKey123")
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the BOUN Archive API"}

@app.get("/api/v1/search")
def search_courses(
    q: str = "",
    term: List[str] = Query(None),
    dept: List[str] = Query(None),
    instructor: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    filter_list = []
    
    if term:
        term_filters = [f"term = '{t}'" for t in term]
        filter_list.append(f"({' OR '.join(term_filters)})")
        
    if dept:
        dept_filters = [f"dept_code = '{d}'" for d in dept]
        filter_list.append(f"({' OR '.join(dept_filters)})")
        
    if instructor:
        filter_list.append(f"instructor = '{instructor}'")

    results = MEILI_CLIENT.index('courses').search(q, {
        'filter': " AND ".join(filter_list) if filter_list else None,
        'limit': limit,
        'offset': offset,
        'facets': ['term', 'dept_code', 'instructor', 'delivery_method'],
        'sort': ['term:desc', 'course_code:asc']
    })
    return results

@app.get("/api/v1/facets")
def get_global_facets():
    # Return facets for all documents (empty search)
    results = MEILI_CLIENT.index('courses').search("", {
        'facets': ['term', 'dept_code', 'delivery_method'],
        'limit': 0
    })
    return results['facetDistribution']

@app.get("/api/v1/analytics/ghost-schedule/{term:path}")
def get_ghost_schedule(
    term: str, 
    dept: List[str] = Query(None),
    db: Session = Depends(database.get_db)
):
    # Reconstruct campus layout for a term
    query = db.query(
        models.CourseSlot.day_code,
        models.CourseSlot.slot_hour,
        models.Room.name.label("room_name"),
        models.Course.course_code,
        models.Course.dept_kisaadi
    ).join(models.Course).join(models.Room).filter(models.Course.term_id == term)
    
    if dept:
        query = query.filter(models.Course.dept_kisaadi.in_(dept))
        
    results = query.all()
    
    # Convert Row objects to dictionaries for JSON serialization
    return [r._asdict() for r in results]

from .analytics import TrendEngine

# Load analytics engine (in a real app, do this once or use a dependency)
def get_engine(db: Session = Depends(database.get_db)):
    # This is heavy for every request, but for demo/small data it's okay.
    # Ideally, pre-calculate or use a subset.
    courses_df = pd.read_sql(db.query(models.Course).statement, db.bind)
    slots_df = pd.read_sql(db.query(models.CourseSlot).statement, db.bind)
    return TrendEngine(courses_df, slots_df)

@app.get("/api/v1/predict/course/{course_code}")
def predict_course(course_code: str, db: Session = Depends(database.get_db)):
    # For performance in this demo, we'll query only the relevant history
    history = db.query(models.Course).filter(models.Course.course_code == course_code).all()
    if not history:
        raise HTTPException(status_code=404, detail="Course not found")
    
    course_ids = [c.id for c in history]
    slots = db.query(models.CourseSlot, models.Course.term_id).join(models.Course).filter(models.CourseSlot.course_id.in_(course_ids)).all()
    
    # Convert to DF for the existing engine logic
    c_df = pd.DataFrame([{
        'id': c.id, 
        'course_code': c.course_code, 
        'term': c.term_id
    } for c in history])
    
    s_df = pd.DataFrame([{
        'course_id': s.CourseSlot.course_id,
        'day': s.CourseSlot.day_code,
        'hour': s.CourseSlot.slot_hour,
        'term': s.term_id
    } for s in slots])
    
    engine = TrendEngine(c_df, s_df)
    return {
        "course_code": course_code,
        "offering_probability": engine.predict_offering(course_code),
        "predicted_slots": engine.predict_slots(course_code)
    }

@app.get("/api/v1/courses/{course_id}", response_model=schemas.Course)
def get_course(course_id: int, db: Session = Depends(database.get_db)):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@app.get("/api/v1/instructors", response_model=List[schemas.Instructor])
def get_instructors(q: str = "", db: Session = Depends(database.get_db)):
    query = db.query(models.Instructor)
    if q:
        query = query.filter(models.Instructor.full_name.ilike(f"%{q}%"))
    return query.limit(50).all()

@app.get("/api/v1/analytics/instructor/{instructor_id}/legacy")
def get_instructor_legacy(instructor_id: int, db: Session = Depends(database.get_db)):
    instructor = db.query(models.Instructor).filter(models.Instructor.id == instructor_id).first()
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor not found")
    
    courses = db.query(models.Course).filter(models.Course.instructor_id == instructor_id).all()
    
    # Calculate legacy metrics
    total_semesters = len(set([c.term_id for c in courses]))
    most_frequent = pd.Series([c.course_code for c in courses]).value_counts().head(5).to_dict()
    
    # Preferred slots (joining with course_slots)
    course_ids = [c.id for c in courses]
    slots = db.query(
        models.CourseSlot.day_code,
        models.CourseSlot.slot_hour
    ).filter(models.CourseSlot.course_id.in_(course_ids)).all()
    
    preferred_slots = pd.DataFrame([{'day': s.day_code, 'hour': s.slot_hour} for s in slots])
    if not preferred_slots.empty:
        slots_count = preferred_slots.groupby(['day', 'hour']).size().reset_index(name='frequency')
        slots_count = slots_count.sort_values(by='frequency', ascending=False).head(5).to_dict(orient='records')
    else:
        slots_count = []

    return {
        "instructor_name": instructor.full_name,
        "total_semesters_taught": total_semesters,
        "total_courses_taught": len(courses),
        "most_frequent_courses": most_frequent,
        "preferred_slots": slots_count,
        "history": sorted([{
            "term": c.term_id,
            "course_code": c.course_code,
            "title": c.title
        } for c in courses], key=lambda x: x['term'], reverse=True)
    }

@app.get("/api/v1/terms", response_model=List[schemas.Term])
def get_terms(db: Session = Depends(database.get_db)):
    return db.query(models.Term).order_by(models.Term.id.desc()).all()

# Additional endpoints will be added here
