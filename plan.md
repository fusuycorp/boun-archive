# Appwrite Migration Plan (boun-archive) - Updated

This plan details the hybrid migration of `boun-archive` to Appwrite BaaS (`https://appwrite.bogazici.app/v1`) per infrastructure ADR-001 & ADR-002 and recent Option B multi-tenant provisioner features in `~/deployment/selfhosted`.

## Overview
- **Hybrid Adoption**: Retain PostgreSQL 16 & Meilisearch v1.12 for read-heavy public course data and analytical engines (`TrendEngine`, `MacroEngine`).
- **Appwrite BaaS**: Delegate User Auth, Session management, Cloud Weekly Schedule Sync, Bookmarks, and Schedule Image/PDF exports.

## Phase Breakdown

### Phase 1: Declarative Schema (`services/boun-archive/appwrite-schema.json`) — STATUS: VERIFIED
- Schema file created at `~/deployment/selfhosted/services/boun-archive/appwrite-schema.json`.
- Configured project `boun-archive` under team `fusuycorp`.
- Verified via `python3 scripts/appwrite_provision.py services/boun-archive/appwrite-schema.json --dry-run` (Exit Code 0).

### Phase 2: SvelteKit Frontend Integration (`frontend/`)
- Install `appwrite` JS Web SDK.
- Create `$lib/appwrite.ts` client & `$lib/stores/auth.svelte.ts` store.
- Add `AuthModal.svelte` for login/magic links.
- Implement 2-way cloud schedule sync in `$routes/calendar/+page.svelte` (keeping `localStorage` guest mode fallback).

### Phase 3: FastAPI Backend Auth Middleware (`backend/`)
- Add `appwrite` Python SDK dependency.
- Add `get_current_user` JWT validation dependency in `backend/app/auth.py`.
- Keep public search and analytics endpoints unauthenticated and fast.

### Phase 4: Docker Swarm Standardization (`docker-stack.yml`)
- Remove host `ports:` bindings.
- Attach frontend/nginx to `dokploy-network` and backend/db to `boun-archive_internal`.
- Add mandatory Host header to container healthchecks (`curl -f -H "Host: $${_APP_DOMAIN}" ...`).
- Pass Appwrite environment variables.
