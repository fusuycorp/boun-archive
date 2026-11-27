<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { page } from "$app/state";
  import { BookOpen, Search, ChevronRight, User, Download, AlertTriangle, RotateCcw } from "lucide-svelte";
  import { API_BASE } from "$lib/config";
  import { exportToCSV } from "$lib/utils";
  import { generateDepartmentsJsonLd, serializeJsonLd } from "$lib/semantic";
  import DeptCourseTable from "$lib/components/departments/DeptCourseTable.svelte";
  import DeptInstructorTable from "$lib/components/departments/DeptInstructorTable.svelte";
  import type { DepartmentUniqueCourse, DepartmentInstructor } from "$lib/types";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();

  let departments = $derived(data.departments ?? []);
  let selectedDept = $state<string | null>(null);
  let uniqueCourses = $state<DepartmentUniqueCourse[]>([]);
  let deptInstructors = $state<DepartmentInstructor[]>([]);
  let loading = $state(false);
  let fetchError = $state<string | null>(null);
  let deptSearch = $state("");
  let viewMode = $state<"courses" | "instructors">("courses");
  let tabCourses = $state<HTMLButtonElement | null>(null);
  let tabInstructors = $state<HTMLButtonElement | null>(null);
  let activeFetchController: AbortController | null = null;

  // Sorting - Courses
  let courseSortColumn = $state<keyof DepartmentUniqueCourse | "latest_term">("latest_term");
  let courseSortDirection = $state<"asc" | "desc">("desc");

  // Sorting - Instructors
  let instructorSortColumn = $state<keyof DepartmentInstructor>("last_term");
  let instructorSortDirection = $state<"asc" | "desc">("desc");

  function syncDeptUrl(dept: string | null, mode: "courses" | "instructors") {
    const params = new URLSearchParams(page.url.searchParams);
    if (dept) params.set("dept", dept);
    else params.delete("dept");
    params.set("view", mode);
    goto(`${page.url.pathname}?${params.toString()}`, {
      replaceState: true,
      noScroll: true,
      keepFocus: true
    });
  }

  const DEPT_CACHE_TTL_MS = 5 * 60 * 1000;

  function parseCachedEnvelope(raw: string): unknown[] | null {
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) return null;
    const envelope = parsed as Record<string, unknown>;
    if (
      typeof envelope.ts !== "number" ||
      !Number.isFinite(envelope.ts) ||
      Date.now() - envelope.ts > DEPT_CACHE_TTL_MS ||
      !Array.isArray(envelope.data) ||
      envelope.data.length === 0
    ) {
      return null;
    }
    return envelope.data;
  }

  function isValidCourseCacheItem(item: unknown): item is DepartmentUniqueCourse {
    if (typeof item !== "object" || item === null) return false;
    const c = item as Record<string, unknown>;
    return (
      typeof c.course_code === "string" &&
      c.course_code.length > 0 &&
      Array.isArray(c.terms) &&
      c.terms.every((t) => typeof t === "string")
    );
  }

  function isValidInstructorCacheItem(item: unknown): item is DepartmentInstructor {
    if (typeof item !== "object" || item === null) return false;
    const i = item as Record<string, unknown>;
    return (
      typeof i.id === "number" &&
      Number.isFinite(i.id) &&
      typeof i.full_name === "string" &&
      i.full_name.length > 0
    );
  }

  function loadCachedDeptData(deptCode: string): { hasCourses: boolean; hasInstructors: boolean } {
    let hasCourses = false;
    let hasInstructors = false;
    try {
      const savedCourses = sessionStorage.getItem(`dept_courses_${deptCode}`);
      if (savedCourses) {
        const items = parseCachedEnvelope(savedCourses);
        if (items && items.every(isValidCourseCacheItem)) {
          const seenCodes = new Set<string>();
          const validUnique = items.filter((c) => {
            if (seenCodes.has(c.course_code)) return false;
            seenCodes.add(c.course_code);
            return true;
          });
          if (validUnique.length > 0) {
            uniqueCourses = validUnique;
            hasCourses = true;
          } else {
            sessionStorage.removeItem(`dept_courses_${deptCode}`);
          }
        } else {
          sessionStorage.removeItem(`dept_courses_${deptCode}`);
        }
      }
    } catch {
      try {
        sessionStorage.removeItem(`dept_courses_${deptCode}`);
      } catch {}
    }
    try {
      const savedInstructors = sessionStorage.getItem(`dept_instructors_${deptCode}`);
      if (savedInstructors) {
        const items = parseCachedEnvelope(savedInstructors);
        if (items && items.every(isValidInstructorCacheItem)) {
          const seenIds = new Set<number>();
          const validUnique = items.filter((i) => {
            if (seenIds.has(i.id)) return false;
            seenIds.add(i.id);
            return true;
          });
          if (validUnique.length > 0) {
            deptInstructors = validUnique;
            hasInstructors = true;
          } else {
            sessionStorage.removeItem(`dept_instructors_${deptCode}`);
          }
        } else {
          sessionStorage.removeItem(`dept_instructors_${deptCode}`);
        }
      }
    } catch {
      try {
        sessionStorage.removeItem(`dept_instructors_${deptCode}`);
      } catch {}
    }
    return { hasCourses, hasInstructors };
  }

  async function fetchDepartmentPayload(deptCode: string, needCourses = true, needInstructors = true) {
    if (activeFetchController) activeFetchController.abort();
    const controller = new AbortController();
    activeFetchController = controller;
    const timeoutId = setTimeout(() => controller.abort(new DOMException("Request timed out", "TimeoutError")), 8000);
    fetchError = null;
    loading = true;

    try {
      const encoded = encodeURIComponent(deptCode);
      const tasks: Promise<void>[] = [];

      if (needCourses) {
        tasks.push((async () => {
          const res = await fetch(`${API_BASE}/v1/departments/${encoded}/unique-courses`, {
            signal: controller.signal
          });
          if (!res.ok) throw new Error(`Courses request failed (HTTP ${res.status})`);
          const payload: DepartmentUniqueCourse[] = await res.json();
          if (controller.signal.aborted) return;
          uniqueCourses = payload.map((c) => ({ ...c, latest_term: c.terms[0] || "" }));
          if (uniqueCourses.length > 0) {
            try {
              sessionStorage.setItem(
                `dept_courses_${deptCode}`,
                JSON.stringify({ ts: Date.now(), data: uniqueCourses })
              );
            } catch {}
          }
        })());
      }

      if (needInstructors) {
        tasks.push((async () => {
          const res = await fetch(`${API_BASE}/v1/departments/${encoded}/instructors`, {
            signal: controller.signal
          });
          if (!res.ok) throw new Error(`Instructors request failed (HTTP ${res.status})`);
          const payload: DepartmentInstructor[] = await res.json();
          if (controller.signal.aborted) return;
          deptInstructors = payload;
          if (deptInstructors.length > 0) {
            try {
              sessionStorage.setItem(
                `dept_instructors_${deptCode}`,
                JSON.stringify({ ts: Date.now(), data: deptInstructors })
              );
            } catch {}
          }
        })());
      }

      await Promise.all(tasks);
    } catch (e) {
      if (e instanceof Error && e.name === "AbortError" && activeFetchController !== controller) {
        return;
      }
      fetchError = e instanceof Error ? e.message : "Failed to load department archive.";
    } finally {
      clearTimeout(timeoutId);
      if (activeFetchController === controller) {
        loading = false;
      }
    }
  }

  function restoreSessionState() {
    try {
      const urlDept = page.url.searchParams.get("dept")?.trim().toUpperCase() || null;
      const urlView = page.url.searchParams.get("view");
      const savedDept = sessionStorage.getItem("dept_selected");
      const savedView = sessionStorage.getItem("dept_view_mode");

      if (urlView === "courses" || urlView === "instructors") {
        viewMode = urlView;
      } else if (savedView === "courses" || savedView === "instructors") {
        viewMode = savedView;
      }

      const initialDept = urlDept || savedDept;
      if (initialDept) {
        selectedDept = initialDept;
        sessionStorage.setItem("dept_selected", initialDept);
        const { hasCourses, hasInstructors } = loadCachedDeptData(initialDept);
        if (!hasCourses || !hasInstructors) {
          fetchDepartmentPayload(initialDept, !hasCourses, !hasInstructors);
        }
        if (!urlDept || !urlView) {
          syncDeptUrl(initialDept, viewMode);
        }
      }
    } catch (e) {
      console.error("Failed to restore session state", e);
    }
  }

  async function handleDeptSelect(deptCode: string) {
    if (!deptCode) return;
    selectedDept = deptCode;
    uniqueCourses = [];
    deptInstructors = [];
    try {
      sessionStorage.setItem("dept_selected", deptCode);
    } catch {}
    syncDeptUrl(deptCode, viewMode);
    await fetchDepartmentPayload(deptCode, true, true);
  }

  function handleCourseSort(column: keyof DepartmentUniqueCourse | "latest_term") {
    if (courseSortColumn === column) {
      courseSortDirection = courseSortDirection === "asc" ? "desc" : "asc";
    } else {
      courseSortColumn = column;
      courseSortDirection = column === "latest_term" ? "desc" : "asc";
    }
  }

  function handleInstructorSort(column: keyof DepartmentInstructor) {
    if (instructorSortColumn === column) {
      instructorSortDirection = instructorSortDirection === "asc" ? "desc" : "asc";
    } else {
      instructorSortColumn = column;
      instructorSortDirection = column === "last_term" ? "desc" : "asc";
    }
  }

  function setViewMode(mode: "courses" | "instructors") {
    viewMode = mode;
    try {
      sessionStorage.setItem("dept_view_mode", mode);
    } catch {}
    syncDeptUrl(selectedDept, mode);
  }

  function handleViewTabKeydown(e: KeyboardEvent, current: "courses" | "instructors") {
    if (e.key === "ArrowRight" || e.key === "ArrowLeft" || e.key === "Home" || e.key === "End") {
      e.preventDefault();
      const next =
        e.key === "Home"
          ? "courses"
          : e.key === "End"
          ? "instructors"
          : current === "courses"
          ? "instructors"
          : "courses";
      setViewMode(next);
      (next === "courses" ? tabCourses : tabInstructors)?.focus();
    }
  }

  function handleExport() {
    if (viewMode === 'courses') {
      if (uniqueCourses.length === 0) return;
      const exportData = sortedCourses.map(c => ({
        course_code: c.course_code,
        title: c.title,
        latest_term: c.latest_term,
        all_terms: c.terms.join('; ')
      }));
      exportToCSV(exportData, `boun_dept_${selectedDept}_courses_${new Date().toISOString().split('T')[0]}`);
    } else {
      if (deptInstructors.length === 0) return;
      const exportData = sortedInstructors.map(i => ({
        full_name: i.full_name,
        last_term: i.last_term,
        course_count: i.course_count,
        total_semesters: i.total_semesters
      }));
      exportToCSV(exportData, `boun_dept_${selectedDept}_instructors_${new Date().toISOString().split('T')[0]}`);
    }
  }

  onMount(() => {
    restoreSessionState();
    return () => {
      activeFetchController?.abort();
    };
  });

  const filteredDepts = $derived(
    departments.filter(d => 
      d.kisaadi.toLowerCase().includes(deptSearch.toLowerCase()) || 
      d.bolum.toLowerCase().includes(deptSearch.toLowerCase())
    )
  );

  const sortedCourses = $derived(
    [...uniqueCourses].sort((a, b) => {
      const valA = a[courseSortColumn] ?? "";
      const valB = b[courseSortColumn] ?? "";
      if (valA < valB) return courseSortDirection === "asc" ? -1 : 1;
      if (valA > valB) return courseSortDirection === "asc" ? 1 : -1;
      return 0;
    })
  );

  const sortedInstructors = $derived(
    [...deptInstructors].sort((a, b) => {
      const valA = a[instructorSortColumn] ?? "";
      const valB = b[instructorSortColumn] ?? "";
      if (valA < valB) return instructorSortDirection === "asc" ? -1 : 1;
      if (valA > valB) return instructorSortDirection === "asc" ? 1 : -1;
      return 0;
    })
  );
</script>

<svelte:head>
  <title>Academic Departments Directory • BOUN Archive</title>
  <meta name="description" content="Explore Boğaziçi University academic departments, historical curriculum records, unique course offerings, and faculty instructors." />
  <meta property="og:title" content="Departments Directory • BOUN Archive" />
  <meta property="og:description" content="Explore Boğaziçi University academic departments, historical curriculum records, unique course offerings, and faculty instructors." />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="https://bountools.com/departments" />
  {#if departments.length > 0}
    {@html `<script type="application/ld+json">${serializeJsonLd(generateDepartmentsJsonLd(departments))}<\/script>`}
  {/if}
</svelte:head>

<div class="space-y-6 sm:space-y-8">
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
    <div>
      <h1 class="font-serif text-2xl sm:text-3xl font-bold text-[#002d72] dark:text-slate-50 tracking-tight">Department Archive</h1>
      <p class="font-sans text-xs sm:text-sm text-[#525f7f] dark:text-slate-400 mt-1">Explore course catalogs and faculty rosters across decades of academic history.</p>
    </div>
  </div>

  <!-- Mobile Department Selector (lg:hidden) -->
  <div class="block lg:hidden bg-white p-4 rounded-xl border border-[#e5e0d8] shadow-2xs dark:bg-[#121827] dark:border-[#1e293b] space-y-2">
    <label for="mobile-dept-select" class="font-mono text-[9px] font-bold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider px-1">Choose Department</label>
    <div class="relative">
      <select 
        id="mobile-dept-select"
        value={selectedDept || ""} 
        onchange={(e) => handleDeptSelect(e.currentTarget.value)}
        class="w-full p-2.5 bg-[#faf8f5] border border-[#e5e0d8] rounded-lg text-xs font-semibold text-[#161e2e] outline-none focus:ring-1 focus:ring-[#002d72] dark:bg-[#0a0e1a] dark:border-[#1e293b] dark:text-slate-200 cursor-pointer font-mono"
      >
        <option value="" disabled>-- Select a Department --</option>
        {#each departments as dept}
          <option value={dept.kisaadi}>{dept.kisaadi} - {dept.bolum}</option>
        {/each}
      </select>
    </div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-4 gap-6 lg:gap-8">
    <!-- Desktop Sidebar: Dept List -->
    <aside class="hidden lg:block space-y-4">
      <div class="bg-white rounded-xl border border-[#e5e0d8] shadow-2xs overflow-hidden dark:bg-[#121827] dark:border-[#1e293b] flex flex-col h-[calc(100vh-200px)] sticky top-24">
        <div class="p-3.5 border-b border-[#e5e0d8] dark:border-[#1e293b] bg-[#f3efe6]/60 dark:bg-[#0a0e1a]">
          <div class="relative">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-[#525f7f]" size={15} />
            <input 
              type="text" 
              bind:value={deptSearch}
              placeholder="Search departments..."
              class="w-full pl-9 pr-3 py-2 bg-[#faf8f5] border border-[#e5e0d8] rounded-lg text-xs outline-none focus:ring-1 focus:ring-[#002d72] focus:border-[#002d72] dark:bg-[#0a0e1a] dark:border-[#1e293b] dark:text-white transition-all"
            />
          </div>
        </div>
        
        <div class="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1">
          {#each filteredDepts as dept}
            <button 
              onclick={() => handleDeptSelect(dept.kisaadi)}
              class="w-full text-left p-2.5 rounded-lg transition-colors group cursor-pointer
              {selectedDept === dept.kisaadi 
                ? 'bg-[#002d72]/10 text-[#002d72] dark:bg-[#8cc8ea]/15 dark:text-[#8cc8ea] shadow-2xs font-bold' 
                : 'text-[#525f7f] dark:text-slate-300 hover:bg-[#f3efe6] dark:hover:bg-slate-800/60'}"
            >
              <div class="flex items-center justify-between">
                <div class="flex flex-col">
                  <span class="font-mono text-[10px] font-bold uppercase tracking-wider opacity-70 {selectedDept === dept.kisaadi ? 'text-[#002d72] dark:text-[#8cc8ea] font-black' : ''}">{dept.kisaadi}</span>
                  <span class="text-xs font-semibold truncate max-w-[180px]">{dept.bolum}</span>
                </div>
                <ChevronRight size={14} class="opacity-0 group-hover:opacity-100 transition-opacity text-[#525f7f]" />
              </div>
            </button>
          {/each}
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="lg:col-span-3 space-y-6">
      <div class="sr-only" role="status" aria-live="polite">
        {#if !loading && selectedDept && !fetchError}
          {selectedDept}: showing {viewMode === 'courses' ? `${uniqueCourses.length} courses` : `${deptInstructors.length} instructors`}
        {/if}
      </div>

      {#if loading}
        <div class="bg-white rounded-xl border border-[#e5e0d8] p-20 flex flex-col items-center justify-center space-y-3 dark:bg-[#121827] dark:border-[#1e293b]">
          <div class="animate-spin rounded-full h-8 w-8 border-3 border-[#e5e0d8] border-t-[#002d72] dark:border-slate-800 dark:border-t-[#8cc8ea]"></div>
          <p class="text-[#525f7f] dark:text-slate-400 font-medium text-xs">Retrieving department archive...</p>
        </div>
      {:else if fetchError && selectedDept}
        <div role="alert" class="bg-white rounded-xl border border-rose-300 dark:border-rose-800 p-10 flex flex-col items-center justify-center text-center space-y-3 dark:bg-[#121827]">
          <AlertTriangle size={24} class="text-rose-600 dark:text-rose-400" />
          <h3 class="font-serif text-lg font-bold text-[#161e2e] dark:text-slate-100">Unable to load {selectedDept} archive</h3>
          <p class="text-xs text-[#525f7f] dark:text-slate-400 max-w-md">{fetchError}</p>
          <button
            type="button"
            onclick={() => fetchDepartmentPayload(selectedDept!, true, true)}
            class="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#002d72] text-white text-xs font-semibold hover:bg-[#001b44] transition-colors cursor-pointer"
          >
            <RotateCcw size={13} />
            <span>Retry</span>
          </button>
        </div>
      {:else if selectedDept}
        <div class="bg-white rounded-xl border border-[#e5e0d8] shadow-2xs overflow-hidden dark:bg-[#121827] dark:border-[#1e293b]">
          <div class="p-4 sm:p-5 border-b border-[#e5e0d8] dark:border-[#1e293b] flex flex-col sm:flex-row sm:items-center justify-between bg-[#f3efe6]/60 dark:bg-[#0a0e1a] gap-4">
            <div class="flex items-center space-x-3">
              <div class="w-9 h-9 bg-[#002d72] dark:bg-slate-800 rounded-lg flex items-center justify-center text-white dark:text-[#8cc8ea] shadow-2xs shrink-0">
                {#if viewMode === 'courses'}
                   <BookOpen size={18} />
                {:else}
                   <User size={18} />
                {/if}
              </div>
              <div>
                <h2 class="font-serif text-lg sm:text-xl font-bold text-[#002d72] dark:text-slate-100">{selectedDept} {viewMode === 'courses' ? 'Courses' : 'Instructors'}</h2>
                <p class="font-mono text-xs text-[#525f7f] dark:text-slate-400">
                   {viewMode === 'courses' ? uniqueCourses.length : deptInstructors.length} historical records
                </p>
              </div>
            </div>

            <div class="flex flex-wrap items-center gap-2 sm:gap-3">
              <!-- Tab Switcher -->
              <div role="tablist" aria-label="Department archive view" class="flex bg-[#e5e0d8] dark:bg-slate-800 p-1 rounded-lg">
                 <button 
                  bind:this={tabCourses}
                  id="dept-tab-courses"
                  type="button"
                  role="tab"
                  aria-selected={viewMode === 'courses'}
                  aria-controls="dept-panel-courses"
                  tabindex={viewMode === 'courses' ? 0 : -1}
                  onclick={() => setViewMode('courses')}
                  onkeydown={(e) => handleViewTabKeydown(e, 'courses')}
                  class="px-3 py-1 text-xs font-semibold rounded-md transition-colors cursor-pointer border-b-2 {viewMode === 'courses' ? 'bg-[#002d72] text-white border-[#c5a059] shadow-2xs dark:bg-[#8cc8ea] dark:text-[#0a0e1a] dark:border-[#002d72]' : 'border-transparent text-[#525f7f] hover:text-[#002d72] dark:text-slate-400'}"
                 >Courses</button>
                 <button 
                  bind:this={tabInstructors}
                  id="dept-tab-instructors"
                  type="button"
                  role="tab"
                  aria-selected={viewMode === 'instructors'}
                  aria-controls="dept-panel-instructors"
                  tabindex={viewMode === 'instructors' ? 0 : -1}
                  onclick={() => setViewMode('instructors')}
                  onkeydown={(e) => handleViewTabKeydown(e, 'instructors')}
                  class="px-3 py-1 text-xs font-semibold rounded-md transition-colors cursor-pointer border-b-2 {viewMode === 'instructors' ? 'bg-[#002d72] text-white border-[#c5a059] shadow-2xs dark:bg-[#8cc8ea] dark:text-[#0a0e1a] dark:border-[#002d72]' : 'border-transparent text-[#525f7f] hover:text-[#002d72] dark:text-slate-400'}"
                 >Instructors</button>
              </div>

              <button 
                  type="button"
                  onclick={handleExport}
                  class="flex items-center space-x-1.5 bg-white border border-[#e5e0d8] text-[#161e2e] px-3 py-1.5 rounded-lg text-xs font-semibold hover:bg-[#f3efe6] transition-colors shadow-2xs dark:bg-slate-800 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700 cursor-pointer"
              >
                <Download size={13} />
                <span>Export CSV</span>
              </button>
            </div>
          </div>
          
          {#if viewMode === 'courses'}
            <div id="dept-panel-courses" role="tabpanel" aria-labelledby="dept-tab-courses">
              <DeptCourseTable 
                courses={sortedCourses}
                sortColumn={courseSortColumn}
                sortDirection={courseSortDirection}
                onSort={handleCourseSort}
              />
            </div>
          {:else}
            <div id="dept-panel-instructors" role="tabpanel" aria-labelledby="dept-tab-instructors">
              <DeptInstructorTable 
                instructors={sortedInstructors}
                sortColumn={instructorSortColumn}
                sortDirection={instructorSortDirection}
                onSort={handleInstructorSort}
              />
            </div>
          {/if}
        </div>
      {:else}
        <div class="bg-white rounded-2xl border border-dashed border-[#e5e0d8] p-12 sm:p-24 flex flex-col items-center justify-center text-center dark:bg-[#121827] dark:border-slate-800">
          <div class="w-16 h-16 bg-[#f3efe6] rounded-full flex items-center justify-center text-[#525f7f] mb-4 dark:bg-slate-800 dark:text-slate-500">
            <BookOpen size={28} />
          </div>
          <h3 class="font-serif text-xl sm:text-2xl font-bold text-[#002d72] dark:text-slate-200">Select a Department</h3>
          <p class="font-sans text-xs sm:text-sm text-[#525f7f] dark:text-slate-400 mt-2 max-w-sm">Choose an academic department from the list to view its complete historical curriculum and instructor index.</p>
        </div>
      {/if}
    </main>
  </div>
</div>

<style>
  .custom-scrollbar::-webkit-scrollbar {
    width: 4px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: #e2e8f0;
    border-radius: 10px;
  }
  :global(.dark) .custom-scrollbar::-webkit-scrollbar-thumb {
    background: #334155;
  }
</style>
