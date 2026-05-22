import pandas as pd
import numpy as np
from sqlalchemy import func, distinct, extract, case
from sqlalchemy.orm import Session
from . import models

class TrendEngine:
    def __init__(self, courses_df: pd.DataFrame, slots_df: pd.DataFrame):
        self.courses = courses_df
        self.slots = slots_df

    def predict_offering(self, course_code: str):
        """
        Calculates offering probability per semester type using a 5-year window 
        with exponential decay for better statistical relevance.
        """
        history = self.courses[self.courses['course_code'] == course_code].copy()
        if history.empty:
            return None
        
        # 1. Temporal Analysis
        # Extract year and semester
        history['year'] = history['term'].str.split('/').str[0].astype(int)
        history['semester_num'] = history['term'].str.split('-').str[1].astype(int)
        
        current_year = 2026
        lookback_years = 5
        
        # Filter for the last N years to prioritize recent curriculum changes
        recent_history = history[history['year'] > (current_year - lookback_years)].copy()
        
        # If no recent history, fallback to all time but with warning weight
        if recent_history.empty:
            recent_history = history.copy()
            lookback_years = current_year - history['year'].min()

        # 2. Apply Weighted Decay
        decay_lambda = 0.3
        recent_history['age'] = current_year - recent_history['year']
        recent_history['weight'] = np.exp(-decay_lambda * recent_history['age'])
        
        # 3. Calculate Normalized Probabilities
        semester_weights = recent_history.groupby('semester_num')['weight'].sum()
        total_potential_weight = sum(np.exp(-decay_lambda * i) for i in range(0, lookback_years))
        
        probabilities = {
            "Fall": float(min(1.0, semester_weights.get(1, 0) / total_potential_weight) * 100),
            "Spring": float(min(1.0, semester_weights.get(2, 0) / total_potential_weight) * 100),
            "Summer": float(min(1.0, semester_weights.get(3, 0) / total_potential_weight) * 100)
        }
        
        return probabilities

    def predict_slots(self, course_code: str):
        """
        Predicts likely time slots using a 5-year recency-weighted frequency.
        """
        course_ids = self.courses[self.courses['course_code'] == course_code]['id']
        relevant_slots = self.slots[self.slots['course_id'].isin(course_ids)].copy()
        
        if relevant_slots.empty:
            return []

        # Join with course info to get terms
        relevant_slots = relevant_slots.merge(
            self.courses[['id', 'term']], 
            left_on='course_id', 
            right_on='id', 
            suffixes=('', '_course')
        )

        current_year = 2026
        decay_lambda = 0.3
        relevant_slots['year'] = relevant_slots['term'].str.split('/').str[0].astype(int)
        
        relevant_slots = relevant_slots[relevant_slots['year'] > (current_year - 5)].copy()
        if relevant_slots.empty:
             relevant_slots = self.slots[self.slots['course_id'].isin(course_ids)].copy()
             relevant_slots = relevant_slots.merge(self.courses[['id', 'term']], left_on='course_id', right_on='id')
             relevant_slots['year'] = relevant_slots['term'].str.split('/').str[0].astype(int)

        relevant_slots['age'] = current_year - relevant_slots['year']
        relevant_slots['weight'] = np.exp(-decay_lambda * relevant_slots['age'])

        grouped = relevant_slots.groupby(['day', 'hour'])['weight'].sum().reset_index()
        grouped = grouped.sort_values(by='weight', ascending=False).head(3)
        
        total_weight = grouped['weight'].sum()
        grouped['confidence_score'] = grouped['weight'] / total_weight if total_weight > 0 else 0

        return grouped[['day', 'hour', 'confidence_score']].to_dict(orient='records')

class MacroEngine:
    """
    High-performance engine for university-wide historical analytics.
    Uses SQLAlchemy for direct DB aggregations.
    """
    
    @staticmethod
    def get_department_evolution(db: Session):
        # We want count of courses per department per year
        # Term ID format: "2024/2025-1" -> Year is "2024"
        
        # Subquery to extract year from term_id
        # Note: SQLite vs Postgres substring logic differs slightly. 
        # Using a more robust approach: taking the first 4 chars.
        results = db.query(
            models.Course.dept_kisaadi,
            func.substr(models.Course.term_id, 1, 4).label('year'),
            func.count(models.Course.id).label('count')
        ).group_by(
            models.Course.dept_kisaadi,
            'year'
        ).all()
        
        # Format for Chart.js (Pivot-like structure)
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
    def get_delivery_evolution(db: Session):
        results = db.query(
            func.substr(models.Course.term_id, 1, 4).label('year'),
            models.Course.delivery_method,
            func.count(models.Course.id).label('count')
        ).group_by(
            'year',
            models.Course.delivery_method
        ).all()
        
        # Normalize delivery methods (Standard, Online, Hybrid)
        data = {}
        all_years = sorted(list(set(r.year for r in results)))
        
        for r in results:
            method = r.delivery_method or "Standard"
            if method not in data:
                data[method] = {y: 0 for y in all_years}
            data[method][r.year] += r.count
            
        return {
            "years": all_years,
            "methods": data
        }

    @staticmethod
    def get_scheduling_heatmap(db: Session, decade: int = None):
        query = db.query(
            models.CourseSlot.day_code,
            models.CourseSlot.slot_hour,
            func.count(models.CourseSlot.id).label('count')
        ).join(models.Course)
        
        if decade:
            start_year = str(decade)
            end_year = str(decade + 9)
            query = query.filter(models.Course.term_id >= start_year, models.Course.term_id <= end_year)
            
        results = query.group_by(
            models.CourseSlot.day_code,
            models.CourseSlot.slot_hour
        ).all()
        
        return [r._asdict() for r in results]

    @staticmethod
    def get_course_lifecycles(db: Session):
        # Current state: 2024/2025-1
        # Extinct: Not offered in 10 years
        # New: First offered in last 2 years
        
        all_courses = db.query(
            models.Course.course_code,
            func.min(func.substr(models.Course.term_id, 1, 4)).label('first_seen'),
            func.max(func.substr(models.Course.term_id, 1, 4)).label('last_seen')
        ).group_by(models.Course.course_code).all()
        
        current_year = 2024 # Based on latest data in DB
        
        new_courses = [c.course_code for c in all_courses if int(c.first_seen) >= (current_year - 2)]
        extinct_courses = [c.course_code for c in all_courses if int(c.last_seen) <= (current_year - 10)]
        
        return {
            "new": new_courses[:50], # Limit for UI
            "extinct": extinct_courses[:50],
            "total_new": len(new_courses),
            "total_extinct": len(extinct_courses)
        }
