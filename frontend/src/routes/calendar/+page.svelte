<script lang="ts">
  import { onMount } from "svelte";
  import { Search, Calendar, Plus, Trash2, AlertTriangle, Check, MapPin, BookOpen, Clock, RotateCcw } from "lucide-svelte";
  import { API_BASE } from "$lib/config";

  // State
  let terms = $state<any[]>([]);
  let selectedTerm = $state("");
  let searchQuery = $state("");
  let searchResults = $state<any[]>([]);
  let myCourses = $state<any[]>([]);
  let loading = $state(false);
  let mobileTab = $state<"schedule" | "courses">("schedule");
  let days = ["M", "T", "W", "Th", "F", "St", "Su"];
  let hours = Array.from({ length: 14 }, (_, i) => i + 1);

  function loadCoursesForTerm(term: string) {
    if (!term) {
      myCourses = [];
      return;
    }
    try {
      const saved = localStorage.getItem(`planner_${term}`);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          myCourses = parsed.filter(c => c && (c.id != null || c.course_code != null));
          return;
        }
      }
    } catch (e) {
      console.error("Failed to parse saved planner courses", e);
    }
    myCourses = [];
  }

  function saveCoursesForTerm(term: string, courses: any[]) {
    if (!term) return;
    try {
      localStorage.setItem(`planner_${term}`, JSON.stringify(courses));
    } catch (e) {
      console.error("Failed to save planner courses to localStorage", e);
    }
  }

  function handleTermSelect(newTerm: string) {
    selectedTerm = newTerm;
    searchQuery = "";
    searchResults = [];
    loadCoursesForTerm(newTerm);
    sessionStorage.setItem("planner_selected_term", newTerm);
  }

  async function fetchTerms() {
    try {
      const res = await fetch(`${API_BASE}/v1/terms`);
      if (res.ok) {
        terms = await res.json();
        if (terms.length > 0) {
          const savedTerm = sessionStorage.getItem("planner_selected_term");
          const termToSelect = (savedTerm && terms.some(t => t.id === savedTerm)) ? savedTerm : terms[0].id;
          selectedTerm = termToSelect;
          loadCoursesForTerm(termToSelect);
        }
      }
    } catch (e) {
      console.error("Failed to fetch terms", e);
    }
  }

  async function performSearch() {
    if (searchQuery.trim().length < 2) {
      searchResults = [];
      return;
    }
    loading = true;
    try {
      const params = new URLSearchParams({
        q: searchQuery.trim(),
        term: selectedTerm,
        limit: "100"
      });
      const res = await fetch(`${API_BASE}/v1/search?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        searchResults = data.hits || [];
      }
    } catch (e) {
      console.error("Search failed", e);
    } finally {
      loading = false;
    }
  }

  async function toggleCourse(course: any) {
    const courseId = course.id;
    const isEnrolled = myCourses.some(c => 
      (courseId != null && c.id != null && String(c.id) === String(courseId)) ||
      (c.course_code === course.course_code && c.section === course.section)
    );

    if (isEnrolled) {
      removeCourse(courseId, course.course_code, course.section);
    } else {
      try {
        const res = await fetch(`${API_BASE}/v1/courses/${courseId}`);
        if (res.ok) {
          const detailed = await res.json();
          if (detailed && (detailed.id || detailed.course_code)) {
            myCourses = [...myCourses, detailed];
            saveCoursesForTerm(selectedTerm, myCourses);
            return;
          }
        }
      } catch (e) {
        console.error("Failed to load full course slots, using search payload", e);
      }
      myCourses = [...myCourses, course];
      saveCoursesForTerm(selectedTerm, myCourses);
    }
  }

  function removeCourse(id: any, code?: string, sec?: string) {
    myCourses = myCourses.filter(c => {
      if (id != null && c.id != null && String(c.id) === String(id)) return false;
      if (code && sec && c.course_code === code && c.section === sec) return false;
      if (id != null && !code && String(c.id) === String(id)) return false;
      return true;
    });
    saveCoursesForTerm(selectedTerm, myCourses);
  }

  function clearAllCourses() {
    if (confirm("Clear all enrolled courses from this semester's planner?")) {
      myCourses = [];
      saveCoursesForTerm(selectedTerm, []);
    }
  }

  // Memoized Timetable Map
  const scheduleMatrix = $derived.by(() => {
    const map = new Map<string, any[]>();
    for (const c of myCourses) {
      if (!c || !c.slots) continue;
      for (const s of c.slots) {
        if (!s || !s.day_code || !s.slot_hour) continue;
        const key = `${s.day_code}_${s.slot_hour}`;
        const roomStr = s.room_name || (s.room ? s.room.name : (s.room_id ? `Room ${s.room_id}` : "N/A"));
        const item = {
          ...c,
          slot_type: s.slot_title || "Lecture",
          room_name: roomStr
        };
        if (!map.has(key)) {
          map.set(key, [item]);
        } else {
          map.get(key)!.push(item);
        }
      }
    }
    return map;
  });

  function getCoursesAt(day: string, hour: number) {
    return scheduleMatrix.get(`${day}_${hour}`) || [];
  }

  function isLabOrPS(slotType: string) {
    if (!slotType) return false;
    const type = slotType.toLowerCase();
    return type.includes("lab") || type.includes("ps") || type.includes("practice");
  }

  onMount(fetchTerms);

  let timeout: any;
  function handleInput() {
    clearTimeout(timeout);
    timeout = setTimeout(performSearch, 300);
  }
</script>

<div class="space-y-4 sm:space-y-6 h-full flex flex-col">
  <!-- Header -->
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
    <div>
      <h1 class="font-serif text-2xl sm:text-3xl font-bold text-[#1c1b18] dark:text-neutral-50 tracking-tight">Weekly Planner</h1>
      <p class="font-sans text-xs sm:text-sm text-[#746f65] mt-1 dark:text-neutral-400">Personalize semester schedules and identify timetable conflicts.</p>
    </div>
    
    <div class="flex items-center space-x-3">
      <div class="flex flex-col space-y-1 w-full sm:w-auto">
        <label for="semester-select" class="font-mono text-[9px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider px-1">Selected Semester</label>
        <select 
          id="semester-select"
          value={selectedTerm} 
          onchange={(e) => handleTermSelect(e.currentTarget.value)}
          class="w-full sm:min-w-[180px] p-2 bg-[#f7f5ee] border border-[#dbd7cc] rounded-lg text-xs sm:text-sm font-semibold text-[#1c1b18] outline-none focus:ring-2 focus:ring-[#c5a059]/30 dark:bg-[#18181b] dark:border-[#27272a] dark:text-neutral-100 shadow-2xs cursor-pointer font-mono"
        >
          {#each terms as term}
            <option value={term.id}>{term.id}</option>
          {/each}
        </select>
      </div>
    </div>
  </div>

  <!-- Mobile Segmented View Switcher (lg:hidden) -->
  <div class="lg:hidden flex bg-[#dedacb] dark:bg-[#27272a] p-1 rounded-xl shrink-0 font-sans">
    <button 
      onclick={() => mobileTab = "schedule"}
      class="flex-1 py-2 text-xs font-semibold rounded-lg transition-colors flex items-center justify-center space-x-2 cursor-pointer
      {mobileTab === 'schedule' 
        ? 'bg-[#f7f5ee] text-[#1c1b18] shadow-2xs dark:bg-[#18181b] dark:text-white' 
        : 'text-[#5c5850] dark:text-neutral-400'}"
    >
      <Clock size={14} />
      <span>Timetable Matrix</span>
    </button>
    <button 
      onclick={() => mobileTab = "courses"}
      class="flex-1 py-2 text-xs font-semibold rounded-lg transition-colors flex items-center justify-center space-x-2 cursor-pointer
      {mobileTab === 'courses' 
        ? 'bg-[#f7f5ee] text-[#1c1b18] shadow-2xs dark:bg-[#18181b] dark:text-white' 
        : 'text-[#5c5850] dark:text-neutral-400'}"
    >
      <BookOpen size={14} />
      <span>Courses ({myCourses.length})</span>
    </button>
  </div>

  <!-- Content Body -->
  <div class="flex-1 flex flex-col lg:flex-row gap-4 sm:gap-6 min-h-0 overflow-hidden">
    <!-- Left Sidebar: Search & List -->
    <aside class="w-full lg:w-80 flex flex-col space-y-4 shrink-0 overflow-y-auto pr-0 lg:pr-1 custom-scrollbar {mobileTab === 'courses' ? 'flex' : 'hidden lg:flex'}">
      <!-- Search Box -->
      <div class="bg-[#f7f5ee] p-4 rounded-xl border border-[#dbd7cc] shadow-2xs space-y-3 dark:bg-[#18181b] dark:border-[#27272a]">
        <div class="relative">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-[#746f65]" size={15} />
          <input 
            type="text" 
            bind:value={searchQuery}
            oninput={handleInput}
            placeholder="Search courses to add..."
            class="w-full pl-9 pr-3 py-2 bg-[#eeece2] border border-[#dbd7cc] rounded-lg text-xs outline-none focus:ring-1 focus:ring-[#c5a059] focus:border-[#c5a059] dark:bg-[#121214] dark:border-[#27272a] dark:text-white"
          />
        </div>

        {#if searchResults.length > 0}
          <div class="space-y-2 max-h-56 overflow-y-auto pr-1 custom-scrollbar">
            {#each searchResults as course}
              {@const isAdded = myCourses.some(c => (c.id != null && course.id != null && String(c.id) === String(course.id)) || (c.course_code === course.course_code && c.section === course.section))}
              <button 
                onclick={() => toggleCourse(course)}
                class="w-full p-2.5 border rounded-lg text-left transition-colors group cursor-pointer
                {isAdded 
                  ? 'bg-[#dedacb] border-[#c8c3b5] dark:bg-[#27272a] dark:border-neutral-600' 
                  : 'bg-[#eeece2]/70 border-[#dbd7cc] hover:bg-[#dedacb] dark:bg-[#121214] dark:border-[#27272a] dark:hover:bg-[#232328]'}"
              >
                <div class="flex justify-between items-start">
                  <div class="flex items-center space-x-1.5">
                    <span class="font-mono text-xs font-bold text-[#002d72] dark:text-neutral-100 uppercase">{course.course_code}</span>
                    <span class="font-mono text-[10px] text-[#746f65] dark:text-neutral-500">Sec {course.section}</span>
                  </div>
                  {#if isAdded}
                    <div class="w-4 h-4 bg-[#002d72] dark:bg-amber-400 rounded-full flex items-center justify-center text-white dark:text-neutral-950 shadow-2xs">
                       <Check size={10} strokeWidth={3} />
                    </div>
                  {:else}
                    <Plus size={13} class="text-[#746f65] group-hover:text-[#1c1b18] dark:text-neutral-500 dark:group-hover:text-neutral-200" />
                  {/if}
                </div>
                <div class="font-serif text-xs text-[#45423b] dark:text-neutral-300 mt-1 line-clamp-1">{course.title}</div>
              </button>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Selected List -->
      <div class="bg-[#f7f5ee] p-4 rounded-xl border border-[#dbd7cc] shadow-2xs flex-1 space-y-3 dark:bg-[#18181b] dark:border-[#27272a]">
        <div class="flex items-center justify-between px-1">
          <h3 class="font-mono text-[10px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider">Enrolled Schedule ({myCourses.length})</h3>
          {#if myCourses.length > 0}
            <button 
              onclick={clearAllCourses}
              class="text-[10px] font-mono font-semibold text-[#746f65] hover:text-rose-600 dark:hover:text-rose-400 flex items-center space-x-1 transition-colors cursor-pointer"
              title="Clear all courses for this semester"
            >
              <RotateCcw size={10} />
              <span>Clear</span>
            </button>
          {/if}
        </div>

        <div class="space-y-2 max-h-72 lg:max-h-none overflow-y-auto pr-1 custom-scrollbar">
          {#each myCourses as course}
            <div class="p-3 bg-[#eeece2]/70 border border-[#dbd7cc] rounded-lg group relative dark:bg-[#121214] dark:border-[#27272a]">
              <div class="flex items-center space-x-2">
                <div class="font-mono text-xs font-bold text-[#002d72] dark:text-neutral-100 uppercase">{course.course_code}</div>
                <div class="font-mono text-[10px] text-[#746f65] dark:text-neutral-500">Sec {course.section}</div>
              </div>
              <div class="font-serif text-xs text-[#45423b] dark:text-neutral-300 mt-1 pr-6">{course.title}</div>
              <button 
                onclick={() => removeCourse(course.id, course.course_code, course.section)}
                class="absolute top-2 right-2 p-1 text-[#746f65] hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded transition-colors cursor-pointer"
                aria-label="Remove course"
              >
                <Trash2 size={13} />
              </button>
            </div>
          {/each}
          {#if myCourses.length === 0}
            <div class="text-center py-10 text-[#a39e93] dark:text-neutral-600">
              <Calendar size={28} class="mx-auto mb-2 opacity-30" />
              <p class="font-sans text-xs">No courses selected yet</p>
            </div>
          {/if}
        </div>
      </div>
    </aside>

    <!-- Main Calendar Grid -->
    <div class="flex-1 bg-[#f7f5ee] rounded-xl border border-[#dbd7cc] shadow-2xs overflow-hidden flex flex-col min-w-0 dark:bg-[#18181b] dark:border-[#27272a] {mobileTab === 'schedule' ? 'flex' : 'hidden lg:flex'}">
      <div class="overflow-auto flex-1 custom-scrollbar">
        <table class="w-full border-collapse table-fixed min-w-[620px]">
          <thead class="sticky top-0 z-20 bg-[#e7e4d9]/90 border-b border-[#dbd7cc] dark:bg-[#121214] dark:border-[#27272a]">
            <tr>
              <th class="p-2 sm:p-2.5 font-mono text-[10px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider w-12 sm:w-14 border-r border-[#dbd7cc] dark:border-[#27272a] sticky left-0 z-30 bg-[#e7e4d9] dark:bg-[#121214]">Slot</th>
              {#each days as day}
                <th class="p-2 sm:p-2.5 font-mono text-[10px] font-bold text-[#746f65] dark:text-neutral-500 uppercase tracking-wider">{day}</th>
              {/each}
            </tr>
          </thead>
          <tbody>
            {#each hours as hour}
              <tr class="border-b border-[#dbd7cc]/70 last:border-0 dark:border-[#27272a]">
                <td class="p-2 text-center font-mono text-xs font-bold text-[#746f65] dark:text-neutral-500 border-r border-[#dbd7cc] dark:border-[#27272a] bg-[#e7e4d9]/60 dark:bg-[#121214] sticky left-0 z-10">{hour}</td>
                {#each days as day}
                  {@const slotCourses = getCoursesAt(day, hour)}
                  <td class="p-1 h-20 sm:h-24 align-top relative">
                    <div class="flex flex-col gap-1 h-full">
                      {#each slotCourses as course}
                        {@const isSpecial = isLabOrPS(course.slot_type)}
                        <div 
                          class="p-1.5 rounded-lg border text-[9px] sm:text-[10px] leading-tight flex-1 flex flex-col justify-center
                          {slotCourses.length > 1 
                            ? 'bg-rose-500/10 border-rose-500/30 text-rose-950 dark:bg-rose-500/20 dark:border-rose-500/40 dark:text-rose-200' 
                            : isSpecial 
                              ? 'bg-amber-500/10 border-amber-500/30 text-amber-950 dark:bg-amber-500/15 dark:border-amber-500/30 dark:text-amber-200' 
                              : 'bg-[#002d72]/10 border-[#002d72]/20 text-[#002d72] dark:bg-amber-400/10 dark:border-amber-400/20 dark:text-amber-300'}"
                        >
                          <div class="flex justify-between items-start">
                            <div class="font-mono font-bold truncate">{course.course_code}</div>
                            <div class="font-mono text-[8px] opacity-60">S{course.section}</div>
                          </div>
                          <!-- Display room name directly inside slot -->
                          <div class="font-mono text-[8px] opacity-75 mt-0.5 truncate flex items-center space-x-0.5">
                            <MapPin size={8} class="shrink-0" />
                            <span>{course.room_name}</span>
                          </div>
                          <div class="flex justify-between items-center mt-0.5 border-t border-black/5 dark:border-white/5 pt-0.5 font-mono text-[7px] sm:text-[8px] uppercase">
                            <span class="opacity-75">{course.slot_type || 'Lecture'}</span>
                            {#if slotCourses.length > 1}
                              <AlertTriangle size={8} class="text-rose-600" />
                            {/if}
                          </div>
                        </div>
                      {/each}
                    </div>
                  </td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>

