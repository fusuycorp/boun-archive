import pandas as pd
import numpy as np

class TrendEngine:
    def __init__(self, courses_df: pd.DataFrame, slots_df: pd.DataFrame):
        self.courses = courses_df
        self.slots = slots_df

    def predict_offering(self, course_code: str):
        """
        Calculates offering probability per semester type based on historical frequency.
        """
        history = self.courses[self.courses['course_code'] == course_code]
        if history.empty:
            return None
        
        # Count by semester number (1: Fall, 2: Spring, 3: Summer)
        # Assuming term format is 'YYYY/YYYY-N'
        history['semester_num'] = history['term'].str.split('-').str[1].astype(int)
        
        # Get unique years for the course
        years = history['term'].str.split('/').str[0].nunique()
        
        counts = history.groupby('semester_num')['id'].nunique()
        
        probabilities = {
            "Fall": float((counts.get(1, 0) / years) * 100),
            "Spring": float((counts.get(2, 0) / years) * 100),
            "Summer": float((counts.get(3, 0) / years) * 100)
        }
        
        return probabilities

    def predict_slots(self, course_code: str):
        """
        Predicts likely time slots using recency-weighted frequency.
        """
        course_ids = self.courses[self.courses['course_code'] == course_code]['id']
        relevant_slots = self.slots[self.slots['course_id'].isin(course_ids)].copy()
        
        if relevant_slots.empty:
            return []

        # Join with course info to get terms for weighting
        relevant_slots = relevant_slots.merge(
            self.courses[['id', 'term']], 
            left_on='course_id', 
            right_on='id', 
            suffixes=('', '_course')
        )

        # Simple recency weight: 
        # Extract year and calculate weight (1.5x for last 3 years, 1.0 otherwise)
        # Note: This is a placeholder for more complex decay functions
        current_year = 2024
        relevant_slots['year'] = relevant_slots['term'].str.split('/').str[0].astype(int)
        relevant_slots['weight'] = relevant_slots['year'].apply(
            lambda y: 1.5 if (current_year - y) <= 3 else 1.0
        )

        # Group by day and hour
        grouped = relevant_slots.groupby(['day', 'hour'])['weight'].sum().reset_index()
        grouped = grouped.sort_values(by='weight', ascending=False).head(3)
        
        # Normalize score
        total_weight = grouped['weight'].sum()
        grouped['confidence_score'] = grouped['weight'] / total_weight

        return grouped[['day', 'hour', 'confidence_score']].to_dict(orient='records')

# Unit test / usage check
if __name__ == "__main__":
    import sqlite3
    conn = sqlite3.connect('schedules.db')
    c_df = pd.read_sql_query("SELECT * FROM courses", conn)
    s_df = pd.read_sql_query("SELECT * FROM course_slots", conn)
    
    engine = TrendEngine(c_df, s_df)
    print(f"Predictions for INTT514:")
    print(engine.predict_offering("INTT514"))
    print(engine.predict_slots("INTT514"))
