# Migration Task Checklist

- [ ] **Phase 1: Declarative Schema**
  - [ ] Create `services/boun-archive/appwrite-schema.json` in `~/deployment/selfhosted`
  - [ ] Run provision script `python3 scripts/appwrite_provision.py`

- [ ] **Phase 2: Frontend Appwrite Integration**
  - [ ] Install `appwrite` SDK in `frontend/package.json`
  - [ ] Add `frontend/src/lib/appwrite.ts`
  - [ ] Add `frontend/src/lib/stores/auth.svelte.ts`
  - [ ] Add `frontend/src/lib/components/AuthModal.svelte`
  - [ ] Update `frontend/src/routes/calendar/+page.svelte` for 2-way cloud schedule sync

- [ ] **Phase 3: Backend Auth Middleware**
  - [ ] Add `appwrite` Python dependency
  - [ ] Add `backend/app/auth.py` for JWT validation

- [ ] **Phase 4: Docker Stack Alignment**
  - [ ] Update `docker-stack.yml` (remove `ports:`, set Host headers on healthchecks)
  - [ ] Update `.env.example` with `PUBLIC_APPWRITE_ENDPOINT` and `PUBLIC_APPWRITE_PROJECT_ID`

- [ ] **Phase 5: Verification & Testing**
  - [ ] Run `bun check` on frontend
  - [ ] Run backend tests/healthcheck
