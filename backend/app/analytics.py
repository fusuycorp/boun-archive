import math
from collections import Counter
from sqlalchemy import func, distinct, extract, case
from sqlalchemy.orm import Session
from . import models

class TrendEngine:
    def __init__(self, courses: list, slots: list):
        # courses is a list of dicts: [{'id': int, 'course_code': str, 'term': str}]
        # slots is a list of dicts: [{'course_id': int, 'day': str, 'hour': int, 'term': str}]
        self.courses = courses
        self.slots = slots

    def predict_offering(self, course_code: str):
        """
        Calculates offering probability per semester type using a 5-year window 
        with exponential decay for better statistical relevance.
        """
        history = [c for c in self.courses if c['course_code'] == course_code]
        if not history:
            return None
        
        current_year = 2026
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

        current_year = 2026
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

        sorted_slots = sorted(slot_weights.items(), key=lambda x: x[1], reverse=True)[:3]
        total_weight = sum(w for _, w in sorted_slots)
        
        predicted = []
        for (day, hour), w in sorted_slots:
            predicted.append({
                "day": day,
                "hour": hour,
                "confidence_score": float(w / total_weight) if total_weight > 0 else 0.0
            })
            
        return predicted

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
    def get_course_lifecycles(db: Session, extinct_threshold: int = 10, new_threshold: int = 2):
        # Current state: 2024/2025-1
        # Extinct: Not offered in N years (extinct_threshold)
        # New: First offered in last M years (new_threshold)
        
        all_courses = db.query(
            models.Course.course_code,
            func.min(func.substr(models.Course.term_id, 1, 4)).label('first_seen'),
            func.max(func.substr(models.Course.term_id, 1, 4)).label('last_seen')
        ).group_by(models.Course.course_code).all()
        
        current_year = 2024 # Based on latest data in DB
        
        new_courses = [c.course_code for c in all_courses if int(c.first_seen) >= (current_year - new_threshold)]
        extinct_courses = [c.course_code for c in all_courses if int(c.last_seen) <= (current_year - extinct_threshold)]
        
        # Evergreens: first seen >= 15 years ago, and still offered recently (within new_threshold)
        evergreens = [c.course_code for c in all_courses if (current_year - int(c.first_seen) >= 15) and (int(c.last_seen) >= current_year - new_threshold)]
        
        return {
            "new": new_courses[:50], # Limit for UI
            "extinct": extinct_courses[:50],
            "evergreens": evergreens[:50],
            "total_new": len(new_courses),
            "total_extinct": len(extinct_courses),
            "total_evergreens": len(evergreens)
        }

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

# Add migration distribution and semantic shift to MacroEngine
class MacroEngineCampusAndSemantic(MacroEngine):
    @staticmethod
    def get_campus_distribution(db: Session, lookback_years: Optional[int] = None):
        query = db.query(
            models.Room.name.label("room_name"),
            func.substr(models.Course.term_id, 1, 4).label("year")
        ).join(models.CourseSlot, models.Room.slots).join(models.Course, models.CourseSlot.course)
        
        if lookback_years:
            current_year = 2024
            start_year = str(current_year - lookback_years)
            query = query.filter(models.Course.term_id >= start_year)
            
        results = query.all()
        
        campus_counts = {}
        for r in results:
            if not r.room_name or not r.year:
                continue
            campus = resolve_campus(r.room_name)
            year = r.year
            if year not in campus_counts:
                campus_counts[year] = {"South": 0, "North": 0, "Hisar": 0, "Kilyos": 0}
            if campus in campus_counts[year]:
                campus_counts[year][campus] += 1
            
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
        results = db.query(
            models.Course.title,
            func.substr(models.Course.term_id, 1, 4).label("year")
        ).all()
        
        stopwords = {
            "and", "the", "in", "of", "to", "for", "on", "with", "a", "an", "by", "from",
            "at", "about", "as", "into", "its", "or", "study", "studies", "introduction",
            "special", "topics", "seminar", "advanced", "selected", "i", "ii", "iii", "iv",
            "principles", "methods", "systems", "applications", "general", "theory", "practice",
            "lab", "laboratory", "project", "research", "course", "concepts", "problems"
        }
        
        bucket_words = {}
        for r in results:
            if not r.title or not r.year:
                continue
            try:
                year_val = int(r.year)
            except:
                continue
                
            start_year = (year_val // interval_years) * interval_years
            bucket_name = f"{start_year}s" if interval_years == 10 else f"{start_year}-{start_year + interval_years - 1}"
            
            if bucket_name not in bucket_words:
                bucket_words[bucket_name] = []
                
            words = r.title.lower().split()
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

# Re-assign methods to MacroEngine to preserve references
MacroEngine.get_campus_distribution = MacroEngineCampusAndSemantic.get_campus_distribution
MacroEngine.get_semantic_shift = MacroEngineCampusAndSemantic.get_semantic_shift

