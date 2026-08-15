# Plan: Fix Backend 0/4 Crash Loop & Decouple Startup Migration

## 1. Problem Diagnosis
- **Symptom**: Service is at 0/4 replicas. Replicas .1, .3, .4 are cycling with exit code 137 (SIGKILL by Docker healthcheck failure); replica .2 has been dead for ~2 weeks due to `restart_policy.condition: on-failure` ignoring exit code 0.
- **Root Cause**:
  1. `entrypoint.sh` runs a distributed Redis lock dance (`boun_archive_init_lock`) before starting Uvicorn.
  2. The lock winner runs batch migration of 137k courses and 327k slots, plus Meilisearch syncing, while other replicas wait in a blocking loop.
  3. Because Uvicorn is not yet bound to port 8000, Docker's healthcheck (~150s grace period) marks all replicas unhealthy and issues a SIGKILL (exit 137).
  4. The lock holder is killed mid-migration, leaving the Redis lock active with no completion marker (`boun_archive_init_done`). Replicas entering the restart loop are locked out, wait forever, and get SIGKILL'd in an infinite loop.

## 2. Solution Architecture
- **Web Replicas (Serving)**:
  - `entrypoint.sh` only performs fast socket connectivity pings for PostgreSQL, Redis, and Meilisearch (<1s).
  - Immediately executes Uvicorn. Replicas become healthy and respond to `/health` within 1-2 seconds.
  - Restart policy configured to `condition: any` so all 4 replicas remain active.
- **Database & Index Initialization (Dedicated Task)**:
  - Add an `init` service to `docker-stack.yml` with `replicas: 1` and `restart_policy.condition: on-failure` to run database migration and Meilisearch sync independently of HTTP serving.
  - Add idempotency check to `sync_meilisearch.py` so it skips if documents already exist, and optimize indexing task batching.
- **Healthcheck Standardization**:
  - Update `docker-stack.yml` backend healthcheck to query `/health` directly instead of `/v1/terms`.

## 3. Implementation Steps
1. Modify `backend/entrypoint.sh` to remove lock dance and start Uvicorn immediately after socket verification.
2. Clean up `backend/wait_for_services.py` to remove dead distributed lock polling.
3. Optimize `scripts/sync_meilisearch.py` with fast idempotency checking and asynchronous chunk indexing.
4. Create `scripts/init_db.py` / standalone init script for the migration container.
5. Update `docker-stack.yml` (and `docker-compose.yml`):
   - Add `init` service.
   - Update `backend` healthcheck to `/health`.
   - Update `backend` restart_policy to `condition: any`.
6. Update documentation (`docs/deployment.md`, `README.md`).
7. Run verification checks (`bun check`, `bun run build`).
