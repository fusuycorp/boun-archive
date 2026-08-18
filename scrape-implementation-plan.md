# boun-scrape → boun-archive Sync: Implementation Plan

Written 2026-08-18 from the boun-scrape side, after adding the feed endpoints
this plan consumes. This is the boun-archive-side implementation plan — the
boun-scrape work referenced here is already done and deployed (or ready to
deploy) as of this writing.

## Context

boun-scrape (`~/projects/fusuycorp/boun-scrape`) is a live scraper for the
Boğaziçi registration portal — current-term courses, schedules, and (new)
quota snapshots, plus a delta/change-event log between scrape runs. It does
**not** hold historical data — it only ever scrapes whatever the live portal
currently shows. boun-archive already holds 50+ years of history from another
source; this integration is not about backfilling that, it's about keeping
the *current term* in sync going forward.

Agreed shape (confirmed with the user): a one-time backfill of boun-scrape's
current export, then ongoing incremental (delta + quota) sync scoped to the
current term only — never a full resync of boun-archive's historical corpus.

## Read this first: `migrate_to_pg.py` cannot be reused as-is

`scripts/migrate_to_pg.py` currently does, unconditionally, whenever it
actually executes past its idempotency check:

```python
print("Dropping existing tables...")
Base.metadata.drop_all(engine)
print("Creating tables in PostgreSQL...")
Base.metadata.create_all(engine)
```

This is only safe today because the idempotency check (`SELECT COUNT(*) FROM
courses`, skip if > 0) means it has in practice only ever run once, cold. If
this script is ever invoked again for an incremental sync — e.g. by removing
or bypassing that guard — **it will drop the entire historical archive and
rebuild it from whatever's in the local `schedules.db` at that moment**,
which is only ever current-term data pulled from boun-scrape. This would be
catastrophic and silent (no confirmation prompt, no dry-run).

**Do not extend this script for incremental sync. Write a new ingestion path
that only ever upserts, never drops.** `migrate_to_pg.py` can stay exactly as
it is for the one-time backfill (see Phase 1) since that's the one case where
"empty database, cold load" is actually the correct starting state — but the
ongoing sync job must be new code, not a modification of this script.

Also worth fixing while touching this: `course_records["id"]` currently reuses
boun-scrape's own SQLite autoincrement `courses.id` directly as boun-archive's
primary key. That's fragile across repeated syncs from a source whose IDs can
shift (a boun-scrape DB reset, a re-scrape, etc.). The new ingestion path
should upsert-match on a natural key instead: `(term_id, dept_kisaadi,
course_code, section)`.

## What boun-scrape now exposes (already implemented)

Base URL: `https://scraper.bountools.com/api/v1` (or whatever internal/public
address is reachable from wherever the ingestion job runs — see "Transport"
below).

All of these are currently **public, unauthenticated**. A shared-secret gate
on `/feeds/*` is planned on the boun-scrape side but not yet built — don't
block on it, but don't hardcode assumptions that these stay unauthenticated
forever either (leave room to add an `Authorization`/`X-Feed-Token` header
later without a structural change).

| Endpoint | Purpose | Key params |
|---|---|---|
| `GET /courses` | Full paginated course catalog (current terms only) | `term`, `department`, `page`, `size` |
| `GET /departments` | Department list | — |
| `GET /terms` | List of terms boun-scrape currently holds | — |
| `GET /feeds/exports/{term}/{format}` | One-shot compiled export artifact for a term | `format` = `json` \| `csv` \| `sqlite`/`db` |
| `GET /feeds/deltas` | Course change events (added/removed/modified), **now supports incremental polling** | `term`, `run_id`, **`after_timestamp`** (new), `limit` |
| `GET /feeds/quota-snapshots` | **New.** Captured point-in-time quota readings, append-only log | `term`, **`after_timestamp`**, `limit` (default 500, max 5000) |

`after_timestamp` on both feed endpoints means "strictly after" and compares
against the same string format the entries themselves return in their
`timestamp` (deltas) / `captured_at` (quota) fields — treat it as an opaque
cursor: store whatever the last-seen entry's timestamp string was, pass it
back verbatim next poll. Both endpoints are designed for polling — deltas
still default-sorts newest-first for the general list use case, but
quota-snapshots specifically sorts **oldest-of-the-batch first** (`ASC`) so a
polling consumer can process rows in order and safely advance its cursor to
the last row it saw.

**Quota is opt-in on the boun-scrape side and may be empty for a while.**
Quota snapshot capture only happens when a scrape cycle is triggered with
`capture_quota=true` — it's off by default because bulk quota-fetching is
rate-limited/reCAPTCHA-sensitive against the live portal. Don't assume
`/feeds/quota-snapshots` has data; poll it the same way regardless, it'll
just return `[]` until the boun-scrape operator turns quota capture on.

### `QuotaSnapshotDTO` shape

```json
{
  "term": "2024/2025-1",
  "course_code": "CMPE 150",
  "section": "01",
  "department": "CMPE",
  "status": "Open",
  "quota": "40",
  "current": "35",
  "quota_numeric": 40,
  "current_numeric": 35,
  "is_consent": false,
  "is_unlimited": false,
  "available": 5,
  "captured_at": "2026-08-18 09:15:03"
}
```

Note `department` here is the quota-owning department for this line, which
can differ from the course's own department for cross-listed courses (a
single course/section can have multiple quota-snapshot rows, one per
requiring department — this mirrors how the live quota-check endpoint has
always worked, it's not new behavior).

### `DeltaEventDTO` shape (unchanged, just the new `after_timestamp` filter)

```json
{
  "change_type": "added" | "removed" | "modified",
  "term": "2024/2025-1",
  "department": "CMPE",
  "course_code": "CMPE 150",
  "section": "01",
  "timestamp": "2026-08-18 09:12:44",
  "old_value": { ... } | null,
  "new_value": { ... } | null,
  "details": "..."
}
```

## Schema mapping (good news: it's nearly 1:1 already)

`migrate_to_pg.py` was clearly originally written directly against
boun-scrape's own SQLite export shape — field names match almost exactly.
Reuse this mapping for the new ingestion path too:

| boun-scrape (`courses`) | boun-archive (`Course`) |
|---|---|
| `term` | `term_id` (format `"2024/2025-1"` already matches — `Term.id` parsing splits on the one `-` between year-range and semester number, so no reformatting needed) |
| `department` | `dept_kisaadi` |
| `course_code` | `course_code` (normalize whitespace, same as `migrate_to_pg.py` already does) |
| `section` | `section` |
| `course_name` | `title` |
| `instructor` | resolve/create `Instructor` row by `full_name`, use `instructor_id` |
| `credits`, `ects` | same, cast to `int` |
| `delivery_method` | same |

| boun-scrape (`course_slots`) | boun-archive (`CourseSlot`) |
|---|---|
| `day` | `day_code` |
| `hour` | `slot_hour` (cast to `int`) |
| `room` | resolve/create `Room` row by `name`, use `room_id` |
| `slot_title` | same |

`departments.csv`'s `kisaadi`/`bolum` columns already match boun-scrape's
`DepartmentDTO.code`/`DepartmentDTO.bolum` field names directly.

**No existing tables for quota or deltas.** These need new tables — this is a
real schema decision, not just plumbing:

- A `quota_snapshots` table (or similar): mirror boun-scrape's own shape
  (`term_id`, course FK or `(course_code, section)`, `department`, `status`,
  `quota`, `current`, `quota_numeric`, `current_numeric`, `is_consent`,
  `is_unlimited`, `available`, `captured_at`). Append-only, matches the
  source's log semantics — don't try to collapse to "latest only" unless you
  specifically don't want quota history in boun-archive either.
- A `course_changes`/`deltas` table if you want a change-history view here
  too: `change_type`, `term_id`, course FK or code/section, `timestamp`,
  `old_value`/`new_value` (JSON), `details`.
- A small `sync_state` table: `feed_name` (e.g. `"deltas"`, `"quota_snapshots"`)
  → `last_cursor` (the last `after_timestamp` value successfully processed).
  This is what makes the polling job resumable/idempotent across restarts.

## Transport

boun-archive pulls from boun-scrape (not the reverse) — no new Docker network
wiring needed on either side, since this works over boun-scrape's already-
public API. Confirm at implementation time whether the ingestion job's
container has general outbound internet egress (it should, by default, for
anything not explicitly firewalled) — if it doesn't, that's an infra change
to raise separately, not something to route around in code.

## Phased plan

**Phase 1 — One-time backfill (reuse what exists)**
`schedules.db`/`departments.csv` + `migrate_to_pg.py` already do exactly this
for a cold database. If boun-archive's Postgres already has course rows (the
common case now), this phase is effectively already done — skip straight to
Phase 2. If starting fresh, `migrate_to_pg.py` as-is is fine for this one
step only.

**Phase 2 — New schema**
Add `quota_snapshots`, `course_changes` (or whatever you name it), and
`sync_state` tables/models as sketched above.

**Phase 3 — New incremental ingestion job**
New script (not a modification of `migrate_to_pg.py`), e.g.
`scripts/sync_from_scraper.py`:
1. Read `sync_state` for each feed's last cursor (empty string / unset on
   first run = pull everything currently available).
2. `GET /feeds/deltas?after_timestamp=<cursor>&limit=<page size>`, upsert
   each changed course by natural key `(term_id, dept_kisaadi, course_code,
   section)` — create/update/soft-delete depending on `change_type`.
   Resolve/create `Instructor`/`Room` rows the same way `migrate_to_pg.py`
   does.
3. `GET /feeds/quota-snapshots?after_timestamp=<cursor>&limit=<page size>`,
   insert each row into the new `quota_snapshots` table (append, not upsert —
   it's a log).
4. Advance `sync_state`'s cursor to the last row's timestamp from each feed,
   only after a successful commit of that batch (so a crash mid-batch doesn't
   lose the retry).
5. Paginate if a full page (`limit`) comes back — there may be more.

Run this on a schedule (cron container, matching the `init` job pattern
already used for `migrate_to_pg.py`/`sync_meilisearch.py` — reuse
`backend/entrypoint.sh`'s `exec "$@"` guard pattern, don't regress it, see
`.agents/memory.md`).

**Phase 4 — Meilisearch re-sync**
After each ingestion batch that touched courses, re-run (or incrementally
update) the Meilisearch sync so search/facets reflect the new data. Watch out
for the `joinedload` + `yield_per` incompatibility already fixed once in
`sync_meilisearch.py` (documented in `.agents/memory.md`) — don't reintroduce
it in any new bulk-query code path.

## Open decisions for whoever implements this

- Exact table/column names for the new quota and delta tables (sketched
  above, not finalized).
- Whether quota snapshots get their own frontend surface at all, or stay
  backend-only/analytics-only for now.
- Polling interval and page size for Phase 3's job.
- Whether to add the shared-secret header proactively (cheap, forward-
  compatible) even though boun-scrape doesn't require it yet.
