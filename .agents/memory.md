# Project Memory

## Active Epics & Tasks
- (Add active high-level tasks or milestones here)

## Core Invariants & Architecture Rules
- (Add non-negotiable architecture decisions and constraints here)

## Domain Vocabulary & Gotchas
- `scripts/_pathutil.py` is the single shared helper for sys.path bootstrapping (exports `add_import_paths()`, `SCRIPT_DIR`, `ROOT_DIR`). All of scripts/init_all.py, migrate_to_pg.py, sync_meilisearch.py must use it via `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from _pathutil import ...` — do not re-inline the candidate-path loop.
- Root `pyproject.toml` intentionally keeps `redis` (needed transitively: scripts/init_all.py imports backend/wait_for_services.py which does `import redis`) but must NOT carry `jinja2` (only backend/pyproject.toml needs it, for fastapi-cache2's coder — backend has its own separate venv/lockfile, see backend/README.md's `uv run uvicorn` workflow run from backend/).
- `backend/entrypoint.sh` must keep the `if [ "$#" -gt 0 ]; then exec "$@"; fi` guard near the top — without it, the docker-compose/docker-stack `init` service's `command: ["python", "scripts/init_all.py"]` override is silently discarded and the container falls through to wait_for_services.py + uvicorn instead, so migration/sync never runs. Fixed 2026-08-17; don't regress this when touching entrypoint.sh again.
- `scripts/sync_meilisearch.py`'s Course query used `joinedload(Course.slots)` (a collection) together with `.yield_per(chunk_size)` — SQLAlchemy raises `InvalidRequestError: Can't use yield_per with eager loaders that require uniquing or row buffering`. This means Meilisearch sync had **never actually completed** in any real deployment before 2026-08-17 (masked because entrypoint.sh was separately swallowing the init service's command — see the exec "$@" entry below — so this crash was never hit in practice). Fixed by using `selectinload(Course.slots).joinedload(CourseSlot.room)` instead (verified end-to-end via `docker compose up init`: 136,939 docs indexed).
- `backend/app/main.py` catches `meilisearch.errors.MeilisearchApiError` specifically (not bare `Exception`) around `create_index()` (checks `.code == "index_already_exists"`) and around search/facets calls (checks `.code == "index_not_found"`, raises HTTPException(503) instead of returning a fallback value) — this matters because fastapi-cache2 only caches a successful return, so raising (not returning `{}`) avoids caching a stale "index not ready" state for up to an hour.
