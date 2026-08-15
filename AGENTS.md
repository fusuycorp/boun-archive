# BOUN Archive - Agent Operating Guidelines (AGENTS.md)

## Core Directives

### 1. Pre-Push Local Build Verification (Mandatory)
Before pushing code changes to remote repositories or triggering CI/CD build pipelines, agents MUST empirically verify that the application compiles cleanly without errors:
- **Frontend Build Verification**: Run `bun run build` in `frontend/` to test SvelteKit & Vite/Rolldown production bundling.
- **Type Checking**: Run `bun check` in `frontend/` to verify TypeScript contracts.
- **Dynamic Env Imports**: Avoid `$env/static/public` for dynamic runtime variables; prefer `$env/dynamic/public` with default fallback values so container builds succeed when environment variables are omitted at image build-time.

### 2. Architecture & Code Quality
- **Clean Data Architecture**: Maintain PostgreSQL 16 & Meilisearch for academic analytics, Redis for caching, and local storage for user weekly planner persistence.
- **Simplest Implementation**: No obsolete compatibility layers or speculative abstractions.
- **Clean Git Commits**: Write clean Conventional Git Commits (`feat:`, `fix:`, `docs:`, `refactor:`).
