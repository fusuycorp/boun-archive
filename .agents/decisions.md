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
