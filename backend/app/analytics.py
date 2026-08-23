from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from . import models

class MacroEngine:
    """
    High-performance engine for university-wide historical analytics.
    Uses SQLAlchemy for direct DB aggregations.
    """
    
    @staticmethod
    def get_latest_data_year(db: Session) -> int:
        latest = db.query(func.max(func.substr(models.Course.term_id, 1, 4))).scalar()
        return int(latest) if latest else 0

    @staticmethod
    def get_department_evolution(db: Session):
        # Count of courses per department per academic year (extracted from term_id prefix)
        results = db.query(
            models.Course.dept_kisaadi,
            func.substr(models.Course.term_id, 1, 4).label('year'),
            func.count(models.Course.id).label('count')
        ).group_by(
            models.Course.dept_kisaadi,
            'year'
        ).all()
        
        data = {}
        all_years = sorted(list(set(r.year for r in results)))
        
        for r in results:
            if r.dept_kisaadi not in data:
                data[r.dept_kisaadi] = {y: 0 for y in all_years}
            data[r.dept_kisaadi][r.year] = r.count
            
        return {
            "years": all_years,
            "departments": data
        }

    @staticmethod
    def get_scheduling_heatmap(db: Session, decade: Optional[int] = None):
        query = db.query(
            models.CourseSlot.day_code,
            models.CourseSlot.slot_hour,
            func.count(models.CourseSlot.id).label('count')
        ).join(models.Course)
        
        if decade:
            start_year = str(decade)
            end_year_bound = str(decade + 10)
            query = query.filter(models.Course.term_id >= start_year, models.Course.term_id < end_year_bound)
            
        results = query.group_by(
            models.CourseSlot.day_code,
            models.CourseSlot.slot_hour
        ).all()
        
        return [r._asdict() for r in results]
