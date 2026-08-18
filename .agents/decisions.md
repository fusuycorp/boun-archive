# Architecture Decisions (ADRs)

## Record Format
### [YYYY-MM-DD] ADR-Title
- **Context**: Why was this decision necessary?
- **Decision**: What was chosen?
- **Consequences**: What trade-offs or constraints follow?

## [2026-08-17] Raise instead of return-fallback on cached Meilisearch endpoints
- **Context**: `/v1/search` and `/v1/facets` are decorated with `@cache(expire=600/3600)`. When Meilisearch's `courses` index isn't ready yet (`index_not_found`), the handlers used to `return` an empty/zero result, which fastapi-cache2 then cached for the full TTL — masking real results for up to an hour after the index actually populated.
- **Decision**: On `index_not_found` specifically (checked via `MeilisearchApiError.code`, not string-matching), `raise HTTPException(503)` instead of returning a fallback payload. fastapi-cache2's decorator (`fastapi_cache/decorator.py`) only caches on a successful return — an exception raised before `coder.encode(result)` is never persisted to the cache backend.
- **Consequences**: Clients see a 503 (not a silently-empty 200) while the index is warming up, and stop seeing it immediately once the index exists — no manual cache-bust needed. Same pattern should be used for any future cached endpoint with a "service not ready" fallback: raise, don't return-empty.

## [2026-08-18] boun-scrape Live Feed Ingestion & Natural Key Upserting
- **Context**: `boun-archive` holds 50+ years of historic schedules and requires ongoing synchronization for active academic terms from `boun-scrape` (deltas and quota snapshots). `scripts/migrate_to_pg.py` is destructive (`Base.metadata.drop_all()`) and must not be used for live sync. Furthermore, transient autoincrement integer IDs from `boun-scrape` shift across rescrapes.
- **Decision**: Implemented `scripts/sync_from_scraper.py` using standard library transport (`urllib.request`) and natural composite key matching `(term_id, dept_kisaadi, course_code, section)`. Created `quota_snapshots`, `course_changes`, and `sync_state` tables for append-only quota logs and opaque cursor tracking (`after_timestamp`). Updated backend API with `/v1/courses/{code}/quota` and `/v1/courses/{code}/changes` endpoints, and augmented the course UI page.
- **Consequences**: Ongoing current-term sync is completely non-destructive to historical data, resumable across container restarts, and maintains incremental Meilisearch document updates without requiring full index rebuilds.

