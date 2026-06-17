# BOUN Archive: Frontend Web Application

A SvelteKit (v2) and Svelte (v5) application utilizing Tailwind CSS (v4) to visualize historical course structures, classroom allocations, and scheduling trends.

---

## 1. Features & Routing

The application contains the following routing layout (`src/routes/`):
*   **`/` (Dashboard)**: Dynamic global statistics overview featuring interactive line charts showing department growth over 50 years and a scheduling density heatmap.
*   **`/search`**: Faceted search interface proxying query filters directly to Meilisearch. Auto-synchronizes search query states to URL search parameters for link sharing.
*   **`/departments`**: Directory listing of university bolums (departments) including unique courses offered and active instructor profiles.
*   **`/calendar` (Weekly Planner)**: Personal calendar planner allowing students to build schedule configurations and detect overlapping inter-campus commute conflicts.
*   **`/ghost-schedule`**: Reconstructs physical room mappings hourly for any academic term and visualizes room occupancy rates.
*   **`/trends`**: Forecasts course scheduling patterns using the backend Trend Engine.

---

## 2. Technical Implementations

### A. Svelte 5 State Runes
State management utilizes Svelte 5 runes (`$state()`, `$derived()`, and `$effect()`). Reactive derivations are preferred over effects to avoid cyclic loops and race conditions.

### B. Safe Calendar Storage Persistence
In `src/routes/calendar/+page.svelte`, course calendars are stored in local storage per semester. The save effect untracks `selectedTerm`:
```typescript
  $effect(() => {
    // Untracking selectedTerm prevents saving previous course states into the new term key during term switches
    const term = untrack(() => selectedTerm);
    if (term) {
      localStorage.setItem(`planner_${term}`, JSON.stringify(myCourses));
    }
  });
```
This resolves the bug where switching terms would cause the save effect to run before the load effect, overwriting and destroying semester course lists.

### C. Concurrency Fetch Safety
Interactive configuration controls in the trends view invoke fetches wrapped in `AbortController` controllers:
```typescript
  $effect(() => {
    const controller = new AbortController();
    fetchLifecycles(controller.signal);
    return () => {
      controller.abort(); // Cancel previous request when dependencies re-trigger the effect
    };
  });
```
This ensures that rapid user adjustments cleanly terminate pending fetches, preventing network race conditions.

---

## 3. Development & Build

### Development Server
```bash
# Install dependencies
bun install

# Start development server
bun run dev
```

### Production Build
```bash
# Compile and build production bundle
bun run build

# Preview production build locally
bun run preview
```
