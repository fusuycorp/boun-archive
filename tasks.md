# Maintenance Task Checklist

- [x] **Phase 1: Fix Startup Crash Loop**
  - [x] Decouple DB migrations and Meilisearch indexing from Uvicorn entrypoint
  - [x] Add standalone init task service in `docker-stack.yml` and `docker-compose.yml`
  - [x] Update healthcheck to `/health` and `restart_policy.condition: any`

- [x] **Phase 2: Remove Appwrite Integration**
  - [x] Remove frontend `appwrite` SDK, auth store, AuthModal, and layout headers
  - [x] Keep zero-latency `localStorage` persistence in weekly planner
  - [x] Remove backend `appwrite` dependency and `auth.py`
  - [x] Clean environment configurations and documentation

- [x] **Phase 3: Verification & Quality Assurance**
  - [x] Run `bun check` on frontend (0 errors)
  - [x] Run `bun run build` on frontend (clean production bundle)
  - [x] Verify backend python dependencies and syntax
