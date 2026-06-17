# BOUN Archive: Backend Service

A high-performance FastAPI service designed to query, aggregate, and forecast historical course scheduling data for Bogazici University.

---

## 1. Core Architecture

The backend exposes REST endpoints to retrieve course structures, instructor dna profiles, and aggregated macro metrics. It leverages three main storage systems:
*   **PostgreSQL**: Normalized relational storage for OLTP operations.
*   **Meilisearch**: Faceted full-text search engine for instant directory lookup.
*   **Redis**: High-speed memory storage for endpoint caching.

---

## 2. API Caching Strategy

To achieve sub-millisecond response times for heavy historical aggregations, the backend uses `fastapi-cache2` connected to Redis. 

### A. Custom Key Builder
A custom key builder (`custom_key_builder`) is registered during application startup in `app/main.py`. This key builder filters out any parameters that are instances of `sqlalchemy.orm.Session` (or are named `db`). 
This prevents the unique string representations/memory addresses of database connection instances from causing constant cache misses and Redis key duplication.

---

## 3. Database Indexes

To optimize high-volume queries, indexes are established on the following columns in `app/models.py`:
*   `CourseSlot.day_code` & `CourseSlot.slot_hour` (heavily used for heatmaps and calendar planners).
*   `CourseSlot.course_id` & `CourseSlot.room_id` (foreign keys).
*   `Course.course_code` & `Course.term_id` (filtering course timelines).
*   `Instructor.full_name` (autocomplete autocomplete/case-insensitive search).

---

## 4. Analytical Engines

### A. Trend Engine (Predictive Analytics)
Located in `app/analytics.py` as `TrendEngine`, this class performs:
1.  **Offering Probability**: Calculates the probability of a course being offered in upcoming semesters using a 5-year lookback window and an exponential decay model ($\lambda=0.3$). Standardizes the raw course history by deduplicating entries per academic term to eliminate multi-section inflation.
2.  **Slot Prediction**: Collects scheduling hours, applies decay weights, and normalizes them against the total term offering weights to render accurate confidence scores.

### B. Macro Engine (aggregations)
Located in `app/analytics.py` as `MacroEngine`, this class handles university-wide 50-year trend aggregations. All metrics are aggregated directly inside PostgreSQL using SQL `GROUP BY` and subqueries (e.g. for campus distribution, lifecycles, and semantic shift) to keep the memory utilization flat and protect against Out-Of-Memory (OOM) failures under high-concurrency loads.

---

## 5. Setup & Development

### Virtual Environment Setup
Ensure you have `uv` installed, then run:
```bash
# Install dependencies into virtualenv
uv pip install -e .
```

### Running Server Locally
```bash
# Run server with hot reload
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
