import math
from collections import Counter
from typing import Optional
from sqlalchemy import func, distinct, extract, case, Integer
from sqlalchemy.orm import Session
from . import models

class TrendEngine:
    def __init__(self, courses: list, slots: list):
        # courses is a list of dicts: [{'id': int, 'course_code': str, 'term': str}]
        # slots is a list of dicts: [{'course_id': int, 'day': str, 'hour': int, 'term': str}]
        self.courses = courses
        self.slots = slots
        self.current_year = self._latest_year()

    def _latest_year(self) -> int:
        years = []
        for item in [*self.courses, *self.slots]:
            try:
                years.append(int(item['term'].split('/')[0]))
            except Exception:
                continue
        return max(years) if years else 0

    def predict_offering(self, course_code: str):
        """
        Calculates offering probability per semester type using a 5-year window 
        with exponential decay for better statistical relevance.
        """
        history = [c for c in self.courses if c['course_code'] == course_code]
        if not history:
            return None
        
        current_year = self.current_year
        lookback_years = 5
        decay_lambda = 0.3
        
        # Parse years and semester numbers
        processed_history = []
        for c in history:
            try:
                year = int(c['term'].split('/')[0])
                sem_num = int(c['term'].split('-')[1])
                processed_history.append({
                    'year': year,
                    'semester_num': sem_num
                })
            except Exception:
                continue
                
        if not processed_history:
            return None
            
        # Deduplicate history by (year, semester_num) to prevent multi-section inflation
        seen_terms = set()
        deduped_history = []
        for h in processed_history:
            term_key = (h['year'], h['semester_num'])
            if term_key not in seen_terms:
                seen_terms.add(term_key)
                deduped_history.append(h)
        processed_history = deduped_history
            
        recent_history = [c for c in processed_history if c['year'] > (current_year - lookback_years)]
        if not recent_history:
            recent_history = processed_history
            min_year = min(c['year'] for c in processed_history)
            lookback_years = max(1, current_year - min_year)

        # Calculate decay weights
        semester_weights = {1: 0.0, 2: 0.0, 3: 0.0}
        for c in recent_history:
            age = current_year - c['year']
            weight = math.exp(-decay_lambda * age)
            sem = c['semester_num']
            if sem in semester_weights:
                semester_weights[sem] += weight
                
        total_potential_weight = sum(math.exp(-decay_lambda * i) for i in range(0, lookback_years))
        
        probabilities = {
            "Fall": float(min(1.0, semester_weights.get(1, 0.0) / total_potential_weight) * 100),
            "Spring": float(min(1.0, semester_weights.get(2, 0.0) / total_potential_weight) * 100),
            "Summer": float(min(1.0, semester_weights.get(3, 0.0) / total_potential_weight) * 100)
        }
        
        return probabilities

    def predict_slots(self, course_code: str):
        """
        Predicts likely time slots using a 5-year recency-weighted frequency.
        """
        course_ids = {c['id'] for c in self.courses if c['course_code'] == course_code}
        relevant_slots = [s for s in self.slots if s['course_id'] in course_ids]
        
        if not relevant_slots:
            return []

        current_year = self.current_year
        decay_lambda = 0.3
        
        # Parse years for slots
        processed_slots = []
        for s in relevant_slots:
            try:
                year = int(s['term'].split('/')[0])
                processed_slots.append({
                    'day': s['day'],
                    'hour': s['hour'],
                    'year': year
                })
            except Exception:
                continue
                
        if not processed_slots:
            return []

        recent_slots = [s for s in processed_slots if s['year'] > (current_year - 5)]
        if not recent_slots:
            recent_slots = processed_slots

        slot_weights = {}
        for s in recent_slots:
            if not s['day'] or s['hour'] is None:
                continue
            key = (s['day'], int(s['hour']))
            age = current_year - s['year']
            weight = math.exp(-decay_lambda * age)
            slot_weights[key] = slot_weights.get(key, 0.0) + weight

        # Sort slots by weight descending
        sorted_slots = sorted(slot_weights.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Compute total possible weight based on terms in which the course was actually offered
        terms_with_course = set(s['year'] for s in recent_slots)
        total_possible_weight = sum(math.exp(-decay_lambda * (current_year - y)) for y in terms_with_course)
        
        predicted = []
        for (day, hour), w in sorted_slots:
            confidence = float(w / total_possible_weight) if total_possible_weight > 0 else 0.0
            predicted.append({
                "day": day,
                "hour": hour,
                "confidence_score": min(1.0, confidence)
            })
            
        return predicted

def resolve_campus(room_name: str) -> str:
    if not room_name:
        return "Unknown"
    name = room_name.strip().upper()
    if name.startswith("TB") or name.startswith("IB") or name.startswith("OD") or name.startswith("DODGE") or name.startswith("BTS") or name.startswith("ALBERT") or name.startswith("JF"):
        return "South"
    elif name.startswith("KB") or name.startswith("NH") or name.startswith("ETA") or name.startswith("BM") or name.startswith("BİM") or name.startswith("BIM") or name.startswith("EF") or name.startswith("M ") or name.startswith("M-"):
        return "North"
    elif name.startswith("HB") or name.startswith("HC") or name.startswith("HD") or name.startswith("HK"):
        return "Hisar"
    elif name.startswith("KP") or name.startswith("KYD") or name.startswith("KİLYOS") or name.startswith("KILYOS") or name.startswith("SARITEPE") or name.startswith("SARI"):
        return "Kilyos"
    else:
        if "KILYOS" in name or "SARITEPE" in name:
            return "Kilyos"
        if "HISAR" in name or "HİSAR" in name:
            return "Hisar"
        if name.startswith("M") and len(name) > 1 and (name[1].isdigit() or name[1] == ' '):
            return "North"
        return "South"

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
            end_year_bound = str(decade + 10)
            # Use strict less-than to correctly include the 9th year (e.g. < 2030 includes 2029/2030-1)
            query = query.filter(models.Course.term_id >= start_year, models.Course.term_id < end_year_bound)
            
        results = query.group_by(
            models.CourseSlot.day_code,
            models.CourseSlot.slot_hour
        ).all()
        
        return [r._asdict() for r in results]

    @staticmethod
    def get_course_lifecycles(db: Session, extinct_threshold: int = 10, new_threshold: int = 2):
        # Current state is derived from the newest term in the data.
        # Extinct: Not offered in N years (extinct_threshold)
        # New: First offered in last M years (new_threshold)
        current_year = MacroEngine.get_latest_data_year(db)
        year_expr = func.substr(models.Course.term_id, 1, 4)
        
        # Subquery to aggregate first_seen and last_seen per course_code in SQL
        subq = db.query(
            models.Course.course_code,
            func.min(year_expr).label('first_seen'),
            func.max(year_expr).label('last_seen')
        ).group_by(models.Course.course_code).subquery()
        
        # Query new courses
        new_q = db.query(subq.c.course_code).filter(
            func.cast(subq.c.first_seen, Integer) >= (current_year - new_threshold)
        )
        total_new = new_q.count()
        new_courses = [r[0] for r in new_q.limit(50).all()]
        
        # Query extinct courses
        extinct_q = db.query(subq.c.course_code).filter(
            func.cast(subq.c.last_seen, Integer) <= (current_year - extinct_threshold)
        )
        total_extinct = extinct_q.count()
        extinct_courses = [r[0] for r in extinct_q.limit(50).all()]
        
        # Query evergreens
        evergreen_q = db.query(subq.c.course_code).filter(
            func.cast(subq.c.first_seen, Integer) <= (current_year - 15),
            func.cast(subq.c.last_seen, Integer) >= (current_year - new_threshold)
        )
        total_evergreens = evergreen_q.count()
        evergreens = [r[0] for r in evergreen_q.limit(50).all()]
        
        return {
            "new": new_courses,
            "extinct": extinct_courses,
            "evergreens": evergreens,
            "total_new": total_new,
            "total_extinct": total_extinct,
            "total_evergreens": total_evergreens
        }

    @staticmethod
    def get_campus_distribution(db: Session, lookback_years: Optional[int] = None):
        year_expr = func.substr(models.Course.term_id, 1, 4)
        query = db.query(
            models.Room.name.label("room_name"),
            year_expr.label("year"),
            func.count(models.CourseSlot.id).label("count")
        ).join(models.CourseSlot, models.Room.slots).join(models.Course, models.CourseSlot.course)
        
        if lookback_years:
            current_year = MacroEngine.get_latest_data_year(db)
            start_year = str(current_year - lookback_years)
            query = query.filter(models.Course.term_id >= start_year)
            
        results = query.group_by(models.Room.name, year_expr).all()
        
        campus_counts = {}
        for r_name, r_year, r_count in results:
            if not r_name or not r_year:
                continue
            campus = resolve_campus(r_name)
            if r_year not in campus_counts:
                campus_counts[r_year] = {"South": 0, "North": 0, "Hisar": 0, "Kilyos": 0}
            if campus in campus_counts[r_year]:
                campus_counts[r_year][campus] += r_count
            
        years = sorted(list(campus_counts.keys()))
        return {
            "years": years,
            "South": [campus_counts[y]["South"] for y in years],
            "North": [campus_counts[y]["North"] for y in years],
            "Hisar": [campus_counts[y]["Hisar"] for y in years],
            "Kilyos": [campus_counts[y]["Kilyos"] for y in years]
        }

    @staticmethod
    def get_semantic_shift(db: Session, interval_years: int = 10):
        if not interval_years or interval_years <= 0:
            interval_years = 10
        year_expr = func.substr(models.Course.term_id, 1, 4)
        results = db.query(
            models.Course.title,
            year_expr.label("year")
        ).group_by(models.Course.title, year_expr).all()
        
        stopwords = {
            "and", "the", "in", "of", "to", "for", "on", "with", "a", "an", "by", "from",
            "at", "about", "as", "into", "its", "or", "study", "studies", "introduction",
            "special", "topics", "seminar", "advanced", "selected", "i", "ii", "iii", "iv",
            "principles", "methods", "systems", "applications", "general", "theory", "practice",
            "lab", "laboratory", "project", "research", "course", "concepts", "problems"
        }
        
        bucket_words = {}
        for r_title, r_year in results:
            if not r_title or not r_year:
                continue
            try:
                year_val = int(r_year)
            except:
                continue
                
            start_year = (year_val // interval_years) * interval_years
            bucket_name = f"{start_year}s" if interval_years == 10 else f"{start_year}-{start_year + interval_years - 1}"
            
            if bucket_name not in bucket_words:
                bucket_words[bucket_name] = []
                
            words = r_title.lower().split()
            cleaned_words = []
            for w in words:
                cleaned = "".join(char for char in w if char.isalnum())
                if cleaned and cleaned not in stopwords and len(cleaned) > 2 and not cleaned.isdigit():
                    cleaned_words.append(cleaned)
            bucket_words[bucket_name].extend(cleaned_words)
            
        shift_data = {}
        for bucket, words_list in bucket_words.items():
            if not words_list:
                continue
            word_counts = Counter(words_list)
            top_words = word_counts.most_common(15)
            shift_data[bucket] = [{"word": w, "count": int(c)} for w, c in top_words]
            
        sorted_buckets = sorted(list(shift_data.keys()))
        return {
            "buckets": sorted_buckets,
            "shift": {b: shift_data[b] for b in sorted_buckets}
        }
