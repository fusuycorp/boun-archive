# Migration Task Checklist

- [x] **Phase 1: Declarative Schema**
  - [x] Create `services/boun-archive/appwrite-schema.json` in `~/deployment/selfhosted`
  - [x] Run provision script dry-run `python3 scripts/appwrite_provision.py services/boun-archive/appwrite-schema.json --dry-run`

- [x] **Phase 2: Frontend Appwrite Integration**
  - [x] Install `appwrite` SDK in `frontend/package.json`
  - [x] Add `frontend/src/lib/appwrite.ts`
  - [x] Add `frontend/src/lib/stores/auth.svelte.ts` (Svelte 5 Runes)
  - [x] Add `frontend/src/lib/components/AuthModal.svelte`
  - [x] Update `frontend/src/routes/calendar/+page.svelte` for 2-way cloud schedule sync

- [x] **Phase 3: Backend Auth Middleware**
  - [x] Add `appwrite` Python dependency in `backend/pyproject.toml`
  - [x] Add `backend/app/auth.py` for JWT validation

- [x] **Phase 4: Docker Stack Alignment**
  - [x] Update `docker-stack.yml` (remove host `ports:`, set Host headers on healthchecks per ADR-002)
  - [x] Update `.env.example` with `PUBLIC_APPWRITE_ENDPOINT` and `PUBLIC_APPWRITE_PROJECT_ID`

- [x] **Phase 5: Verification & Testing**
  - [x] Run `bun check` on frontend (0 errors)
  - [x] Verify backend python dependencies & auth syntax
