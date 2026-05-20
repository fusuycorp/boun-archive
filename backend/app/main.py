import os
import meilisearch
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
    term: Optional[str] = None,
    dept: Optional[str] = None,
    instructor: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    filter_list = []
    if term:
        filter_list.append(f"term = '{term}'")
    if dept:
        filter_list.append(f"dept_code = '{dept}'")
    if instructor:
        filter_list.append(f"instructor = '{instructor}'")

    results = MEILI_CLIENT.index('courses').search(q, {
        'filter': " AND ".join(filter_list) if filter_list else None,
        'limit': limit,
        'offset': offset,
        'facets': ['term', 'dept_code', 'instructor', 'delivery_method']
    })
    return results

@app.get("/api/v1/analytics/ghost-schedule/{term}")
def get_ghost_schedule(term: str, db: Session = Depends(database.get_db)):
    # Reconstruct campus layout for a term
    results = db.query(
        models.CourseSlot.day_code,
        models.CourseSlot.slot_hour,
        models.Room.name.label("room_name"),
        models.Course.course_code,
        models.Course.dept_kisaadi
    ).join(models.Course).join(models.Room).filter(models.Course.term_id == term).all()
    
    return results

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

@app.get("/api/v1/terms", response_model=List[schemas.Term])
def get_terms(db: Session = Depends(database.get_db)):
    return db.query(models.Term).all()

# Additional endpoints will be added here
