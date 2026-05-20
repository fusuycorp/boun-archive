import pandas as pd
import numpy as np

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
        # Recent years carry significantly more weight: Weight = e^(-lambda * age)
        # For 5 years, lambda=0.3 gives weights approx: [1.0, 0.74, 0.55, 0.40, 0.30]
        decay_lambda = 0.3
        recent_history['age'] = current_year - recent_history['year']
        recent_history['weight'] = np.exp(-decay_lambda * recent_history['age'])
        
        # 3. Calculate Normalized Probabilities
        # Group by semester and sum weights
        semester_weights = recent_history.groupby('semester_num')['weight'].sum()
        
        # Total potential weight for each semester type over the lookback window
        # (Assuming a course could be offered once per year in each semester)
        total_potential_weight = sum(np.exp(-decay_lambda * i) for i in range(0, lookback_years))
        
        # If we have very little data (e.g. course only offered once 5 years ago), 
        # the probability should reflect that uncertainty.
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
        
        # Filter for 5 years
        relevant_slots = relevant_slots[relevant_slots['year'] > (current_year - 5)].copy()
        if relevant_slots.empty:
             # Fallback if no recent slots
             relevant_slots = self.slots[self.slots['course_id'].isin(course_ids)].copy()
             relevant_slots = relevant_slots.merge(self.courses[['id', 'term']], left_on='course_id', right_on='id')
             relevant_slots['year'] = relevant_slots['term'].str.split('/').str[0].astype(int)

        relevant_slots['age'] = current_year - relevant_slots['year']
        relevant_slots['weight'] = np.exp(-decay_lambda * relevant_slots['age'])

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
