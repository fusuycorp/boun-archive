# Repository Map

Total mapped files: 75

- `.agents/activity.jsonl` (0 B)
- `.agents/decisions.md` (217 B)
- `.agents/memory.md` (288 B)
- `.env.example` (672 B)
- `.github/workflows/deploy.yml` (3103 B)
- `.gitignore` (899 B)
- `.python-version` (5 B)
- `AGENTS.md` (1333 B)
- `BOUN-ARCHIVE-SPEC.md` (7662 B)
- `README.md` (12962 B)
- `backend/.dockerignore` (59 B)
- `backend/.python-version` (5 B)
- `backend/Dockerfile` (1251 B)
- `backend/README.md` (2947 B)
- `backend/app/__init__.py` (0 B)
- `backend/app/analytics.py` (15725 B)
    * class TrendEngine (__init__, _latest_year, predict_offering, predict_slots)
    * def resolve_campus()
    * class MacroEngine (get_latest_data_year, get_department_evolution, get_delivery_evolution, get_scheduling_heatmap, get_course_lifecycles...)
- `backend/app/database.py` (652 B)
    * def get_db()
- `backend/app/main.py` (17105 B)
    * def custom_key_builder()
    * def lifespan()
    * def read_root()
    * def health_check()
    * def search_courses()
    * def get_global_facets()
- `backend/app/models.py` (2590 B)
    * class Term
    * class Department
    * class Instructor
    * class Room
    * class Course
    * class CourseSlot (room_name)
- `backend/app/schemas.py` (1449 B)
    * class TermBase
    * class Term
    * class DepartmentBase
    * class Department
    * class InstructorBase
    * class Instructor
- `backend/entrypoint.sh` (407 B)
- `backend/init_db.sql` (1466 B)
- `backend/main.py` (85 B)
    * def main()
- `backend/pyproject.toml` (617 B)
- `backend/uv.lock` (197599 B)
- `backend/wait_for_services.py` (2118 B)
    * def wait_for_postgres()
    * def wait_for_meilisearch()
    * def wait_for_redis()
- `departments.csv` (5605 B)
- `docker-compose.yml` (3635 B)
- `docker-stack.yml` (5410 B)
- `docs/architecture.md` (3770 B)
- `docs/code-standards.md` (5305 B)
- `docs/deployment.md` (3658 B)
- `docs/environment-variables.md` (1279 B)
- `docs/feature-set.md` (4566 B)
- `frontend/.dockerignore` (119 B)
- `frontend/.gitignore` (210 B)
- `frontend/.npmrc` (19 B)
- `frontend/Dockerfile` (918 B)
- `frontend/README.md` (2836 B)
- `frontend/bun.lock` (53877 B)
- `frontend/package.json` (828 B)
- `frontend/src/app.d.ts` (274 B)
- `frontend/src/app.html` (421 B)
- `frontend/src/lib/assets/favicon.svg` (1569 B)
- `frontend/src/lib/config.ts` (225 B)
    * export const API_BASE
- `frontend/src/lib/index.ts` (75 B)
- `frontend/src/lib/types.ts` (1372 B)
    * export interface Term
    * export interface Department
    * export interface Instructor
    * export interface Room
    * export interface CourseSlot
    * export interface Course
- `frontend/src/lib/utils.ts` (1165 B)
    * export function exportToCSV
    * const headers
    * const csvRows
    * const val
    * const escaped
    * const csvContent
- `frontend/src/routes/+layout.svelte` (6226 B)
- `frontend/src/routes/+page.svelte` (9993 B)
- `frontend/src/routes/calendar/+page.svelte` (18123 B)
- `frontend/src/routes/course/[code]/+page.svelte` (7705 B)
- `frontend/src/routes/departments/+page.svelte` (20483 B)
- `frontend/src/routes/ghost-schedule/+page.svelte` (11954 B)
- `frontend/src/routes/instructor/[id]/+page.svelte` (9671 B)
- `frontend/src/routes/instructors/+page.svelte` (4172 B)
- `frontend/src/routes/layout.css` (687 B)
- `frontend/src/routes/search/+page.svelte` (23074 B)
- `frontend/src/routes/trends/+page.svelte` (34233 B)
- `frontend/static/favicon.png` (367256 B)
- `frontend/static/logo.png` (390785 B)
- `frontend/static/robots.txt` (63 B)
- `frontend/svelte.config.js` (679 B)
    * const config
- `frontend/tsconfig.json` (692 B)
- `frontend/vite.config.ts` (203 B)
- `main.py` (90 B)
    * def main()
- `nginx.conf` (1873 B)
- `plan.md` (2581 B)
- `pyproject.toml` (340 B)
- `scripts/ingest_data.py` (2420 B)
    * def ingest()
- `scripts/init_all.py` (1374 B)
    * def main()
- `scripts/migrate_to_pg.py` (6379 B)
    * def find_data_file()
    * def clean_value()
    * def clean_string()
    * def clean_int()
    * def migrate()
- `scripts/sync_meilisearch.py` (4504 B)
    * def sync_meilisearch()
- `tasks.md` (855 B)
- `uv.lock` (174197 B)