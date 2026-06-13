# BOUN Archive: Project Code Standards

This document defines the backend and frontend coding standards for the BOUN Archive project. As a single-maintainer codebase, these guidelines prioritize **simplicity, reliability, preventability of resource leaks, and self-documenting code**.

---

## 1. Development Philosophy

1.  **Pragmatism over Abstraction**: Avoid deep inheritance hierarchies, generic repositories, or unnecessary design pattern wrappers. Prefer direct, readable code.
2.  **Prevent Resource Exhaustion**: The production stack runs under tight memory constraints (e.g., 1GB backend limit). Never write queries that pull full tables into memory. Use batching, database-level aggregates, and caching.
3.  **Fail Safely**: Ensure that database connections close under all conditions (`try/finally`), network failures show user-friendly fallback boundaries, and missing environment variables crash the app immediately on startup rather than failing silently at runtime.

---

## 2. Backend Coding Standards (FastAPI & Python)

### A. Code Style & Formatting
*   **Formatters**: Strictly adhere to PEP 8. Use **Ruff** or **Black** for auto-formatting.
*   **Type Hinting**: All function signatures, schemas, and return values must contain explicit type hints:
    ```python
    def calculate_decay(age: int, lambda_val: float = 0.3) -> float:
        ...
    ```

### B. Database & ORM (SQLAlchemy v2)
*   **Session Lifecycle**: Always use the FastAPI dependency injection `get_db` to handle sessions. Never instantiate a session inside routes manually.
*   **N+1 Prevention**: Explicitly load relationships. If an endpoint returns slots alongside courses, load them using `joinedload` or `selectinload`:
    ```python
    # Good
    courses = db.query(models.Course).options(
        joinedload(models.Course.slots)
    ).all()
    ```
*   **Prevention of OOM**: Avoid `query.all()` on tables exceeding 5,000 rows. Use aggregates (`func.count`, `func.sum`) or batch queries in chunks using offsets or `yield_per()`.
*   **No Pandas on Live Request Threads**: Never instantiate Pandas DataFrames inside request threads for single-row calculations (e.g. single course predictions). Only use Pandas for macro bulk indexing scripts.

### C. Type Safety & Validation (Pydantic v2)
*   All request bodies and response payloads must utilize Pydantic models extending `BaseModel`.
*   Set `from_attributes = True` inside the Pydantic `Config` class to allow seamless SQLAlchemy model serialization.
*   Keep schemas thin: divide schemas into `Base`, `Create`, and `Response` structures to prevent payload bloat.

### D. Caching Strategy (FastAPI-Cache with Redis)
*   **Heavy Aggregates**: Endpoints compiling historical trends must use `@cache(expire=86400)` (24 hours).
*   **Volatile Queries**: Search and filter endpoints must use `@cache(expire=600)` (10 minutes).
*   **Cache Keys**: Avoid mutable parameters in cache keys. FastAPI-Cache automatically handles cache keys based on endpoint parameters.

---

## 3. Frontend Coding Standards (SvelteKit & Svelte 5)

### A. Svelte 5 Runes Best Practices
*   **Local State**: Use `$state()` for variables modified by UI actions.
*   **Computed State**: Use `$derived()` for any values computed from state variables. Never use `$effect` to modify a state variable based on another state variable.
*   **Side Effects**: Limit `$effect()` usage to synchronization with external systems (such as `localStorage` writes, document theme classes, or DOM event attachments).
*   **Preventing Cyclic Loops**: Never trigger state mutations inside an effect that depends on those same state variables.
    ```typescript
    // BAD (Triggers cycle)
    $effect(() => {
      if (myState) myState = transform(myState);
    });

    // GOOD
    const computedState = $derived(transform(myState));
    ```

### B. Tailwind CSS (v4) & Layout Design
*   **Modern Aesthetics**: Use curated neutral slate and indigo palettes. Avoid loud primary colors.
*   **Custom Scrollbars**: Apply styling using scrollbar utilities to keep scrollbars looking premium.
*   **Dark Mode**: Implement native dark mode classes (`dark:...`). Toggle the class on `document.documentElement` inside a single layout effect.

### C. Client-Side State & URL Mirroring
*   **Shareable Filters**: Any view filtering directories (e.g., [search/+page.svelte](file:///home/devhax/projects/fusuyfusuy/boun-archive/frontend/src/routes/search/+page.svelte)) must sync search queries, offsets, and filters to URL parameters using SvelteKit's `$page.url.searchParams`. Avoid hiding state purely in memory or `sessionStorage` unless it represents a layout layout state.
*   **User Preferences**: Use `localStorage` for weekly planner courses and light/dark theme choices.

---

## 4. DevOps & Setup Standards

### A. Containerization (Docker)
*   **Non-Root Execution**: Both Python and Bun images must run under non-root system users (`USER python` and `USER bun`).
*   **Lockfile Enforcement**: Always build images using `--frozen-lockfile` (Bun) and `uv pip install --system` (Python) to ensure deterministic builds.
*   **Startup Safety Checks**: Ensure all microservices implement a blocking liveness check (e.g. `wait_for_services.py`) to prevent service start crashes if dependencies are booting.
