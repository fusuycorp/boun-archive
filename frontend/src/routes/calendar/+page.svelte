<script lang="ts">
  import { onMount, untrack } from "svelte";
  import { Search, Calendar, Plus, Trash2, AlertTriangle, Check, MapPin, BookOpen, Clock } from "lucide-svelte";
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

  // Persistence: Load courses when selectedTerm changes
  $effect(() => {
    if (selectedTerm) {
      const saved = localStorage.getItem(`planner_${selectedTerm}`);
      if (saved) {
        try {
          myCourses = JSON.parse(saved);
        } catch (e) {
          myCourses = [];
        }
      } else {
        myCourses = [];
      }
    }
  });

  // Persistence: Save courses when myCourses changes
  $effect(() => {
    const term = untrack(() => selectedTerm);
    if (term) {
      localStorage.setItem(`planner_${term}`, JSON.stringify(myCourses));
    }
  });

  async function fetchTerms() {
    try {
      const res = await fetch(`${API_BASE}/v1/terms`);
      if (res.ok) {
        terms = await res.json();
        if (terms.length > 0 && !selectedTerm) {
          selectedTerm = terms[0].id;
        }
      }
    } catch (e) {
      console.error("Failed to fetch terms", e);
    }
  }

  async function performSearch() {
    if (searchQuery.length < 2) return;
    loading = true;
    try {
      const params = new URLSearchParams({
        q: searchQuery,
        term: selectedTerm,
        limit: "200"
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

  async function toggleCourse(courseId: number) {
    if (myCourses.some(c => c.id === courseId)) {
      removeCourse(courseId);
    } else {
      const res = await fetch(`${API_BASE}/v1/courses/${courseId}`);
      const course = await res.json();
      myCourses = [...myCourses, course];
    }
  }

  function removeCourse(id: number) {
    myCourses = myCourses.filter(c => c.id !== id);
  }

  // Memoized Timetable Map
  const scheduleMatrix = $derived.by(() => {
    const map = new Map<string, any[]>();
    for (const c of myCourses) {
      if (!c.slots) continue;
      for (const s of c.slots) {
        const key = `${s.day_code}_${s.slot_hour}`;
        const item = {
          ...c,
          slot_type: s.slot_title || "",
          room_name: s.room_name || "N/A"
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
      <h2 class="text-2xl sm:text-3xl font-black text-slate-800 dark:text-slate-100 tracking-tight">Weekly Planner</h2>
      <p class="text-xs sm:text-sm text-slate-500 mt-1 dark:text-slate-400">Personalize your academic schedule and resolve timetable conflicts.</p>
    </div>
    
    <div class="flex items-center space-x-3">
      <div class="flex flex-col space-y-1 w-full sm:w-auto">
        <label for="semester-select" class="text-[9px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest px-1">Selected Semester</label>
        <select 
          id="semester-select"
          bind:value={selectedTerm} 
          class="w-full sm:min-w-[180px] p-2 bg-white border border-slate-200/80 rounded-xl text-xs sm:text-sm font-bold text-slate-700 outline-none focus:ring-2 focus:ring-[#0080c9] dark:bg-[#0f172a] dark:border-slate-800/80 dark:text-slate-200 shadow-2xs cursor-pointer"
        >
          {#each terms as term}
            <option value={term.id}>{term.id}</option>
          {/each}
        </select>
      </div>
    </div>
  </div>

  <!-- Mobile Segmented View Switcher (lg:hidden) -->
  <div class="lg:hidden flex bg-slate-200/60 dark:bg-slate-800/60 p-1 rounded-xl shrink-0">
    <button 
      onclick={() => mobileTab = "schedule"}
      class="flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center space-x-2 cursor-pointer
      {mobileTab === 'schedule' 
        ? 'bg-white text-[#002d72] shadow-2xs dark:bg-slate-700 dark:text-white' 
        : 'text-slate-600 dark:text-slate-400'}"
    >
      <Clock size={14} />
      <span>Timetable Matrix</span>
    </button>
    <button 
      onclick={() => mobileTab = "courses"}
      class="flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center space-x-2 cursor-pointer
      {mobileTab === 'courses' 
        ? 'bg-white text-[#002d72] shadow-2xs dark:bg-slate-700 dark:text-white' 
        : 'text-slate-600 dark:text-slate-400'}"
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
      <div class="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-2xs space-y-3 dark:bg-[#0f172a] dark:border-slate-800/80">
        <div class="relative">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
          <input 
            type="text" 
            bind:value={searchQuery}
            oninput={handleInput}
            placeholder="Find a course to add..."
            class="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200/80 rounded-xl text-xs sm:text-sm outline-none focus:ring-2 focus:ring-[#0080c9] focus:border-[#0080c9] dark:bg-slate-950 dark:border-slate-800 dark:text-white"
          />
        </div>

        {#if searchResults.length > 0}
          <div class="space-y-2 max-h-56 overflow-y-auto pr-1 custom-scrollbar">
            {#each searchResults as course}
              {@const isAdded = myCourses.some(c => c.id === course.id)}
              <button 
                onclick={() => toggleCourse(course.id)}
                class="w-full p-3 border rounded-xl text-left transition-all group cursor-pointer
                {isAdded 
                  ? 'bg-[#002d72]/10 border-[#002d72]/30 ring-2 ring-[#002d72]/10 dark:bg-sky-500/15 dark:border-sky-500/30 dark:ring-sky-500/20' 
                  : 'bg-slate-50 border-slate-100 hover:bg-[#002d72]/5 hover:border-[#002d72]/20 dark:bg-slate-950 dark:border-slate-800 dark:hover:bg-sky-500/10'}"
              >
                <div class="flex justify-between items-start">
                  <div class="flex items-center space-x-2">
                    <span class="text-xs font-black text-[#002d72] dark:text-sky-400 uppercase">{course.course_code}</span>
                    <span class="text-[10px] text-slate-400 dark:text-slate-500 font-bold">Sec {course.section}</span>
                  </div>
                  {#if isAdded}
                    <div class="w-5 h-5 bg-[#002d72] dark:bg-sky-500 rounded-full flex items-center justify-center text-white shadow-2xs">
                       <Check size={12} strokeWidth={4} />
                    </div>
                  {:else}
                    <Plus size={14} class="text-slate-300 group-hover:text-[#002d72] dark:text-slate-600 dark:group-hover:text-sky-400" />
                  {/if}
                </div>
                <div class="text-xs font-bold text-slate-700 dark:text-slate-300 mt-1 line-clamp-1">{course.title}</div>
              </button>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Selected List -->
      <div class="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-2xs flex-1 space-y-3 dark:bg-[#0f172a] dark:border-slate-800/80">
        <h3 class="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest px-1">My Courses ({myCourses.length})</h3>
        <div class="space-y-2 max-h-72 lg:max-h-none overflow-y-auto pr-1 custom-scrollbar">
          {#each myCourses as course}
            <div class="p-3 bg-white border border-slate-100 rounded-xl group relative dark:bg-slate-950 dark:border-slate-800/80 shadow-2xs">
              <div class="flex items-center space-x-2">
                <div class="text-xs font-black text-[#002d72] dark:text-sky-400 uppercase">{course.course_code}</div>
                <div class="text-[10px] text-slate-400 dark:text-slate-500 font-bold">Section {course.section}</div>
              </div>
              <div class="text-xs font-bold text-slate-700 dark:text-slate-300 mt-1 pr-6">{course.title}</div>
              <button 
                onclick={() => removeCourse(course.id)}
                class="absolute top-2 right-2 p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/40 rounded-lg transition-colors cursor-pointer"
                aria-label="Remove course"
              >
                <Trash2 size={14} />
              </button>
            </div>
          {/each}
          {#if myCourses.length === 0}
            <div class="text-center py-10 text-slate-300 dark:text-slate-600">
              <Calendar size={32} class="mx-auto mb-2 opacity-20" />
              <p class="text-xs font-medium">Your planner is empty</p>
            </div>
          {/if}
        </div>
      </div>
    </aside>

    <!-- Main Calendar Grid -->
    <div class="flex-1 bg-white rounded-2xl border border-slate-200/80 shadow-2xs overflow-hidden flex flex-col min-w-0 dark:bg-[#0f172a] dark:border-slate-800/80 {mobileTab === 'schedule' ? 'flex' : 'hidden lg:flex'}">
      <div class="overflow-auto flex-1 custom-scrollbar">
        <table class="w-full border-collapse table-fixed min-w-[620px]">
          <thead class="sticky top-0 z-20 bg-slate-50 border-b border-slate-200 dark:bg-slate-950 dark:border-slate-800">
            <tr>
              <th class="p-2 sm:p-3 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest w-12 sm:w-16 border-r border-slate-200 dark:border-slate-800 sticky left-0 z-30 bg-slate-50 dark:bg-slate-950">Hr</th>
              {#each days as day}
                <th class="p-2 sm:p-3 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">{day}</th>
              {/each}
            </tr>
          </thead>
          <tbody>
            {#each hours as hour}
              <tr class="border-b border-slate-100 last:border-0 dark:border-slate-800/60">
                <td class="p-2 text-center text-xs font-black text-slate-300 dark:text-slate-600 border-r border-slate-200 dark:border-slate-800 bg-slate-50/90 dark:bg-slate-950/90 sticky left-0 z-10">{hour}</td>
                {#each days as day}
                  {@const slotCourses = getCoursesAt(day, hour)}
                  <td class="p-1 h-20 sm:h-24 vertical-align-top relative">
                    <div class="flex flex-col gap-1 h-full font-sans">
                      {#each slotCourses as course}
                        {@const isSpecial = isLabOrPS(course.slot_type)}
                        <div 
                          class="p-1.5 rounded-lg border text-[9px] sm:text-[10px] leading-tight flex-1 flex flex-col justify-center
                          {slotCourses.length > 1 
                            ? 'bg-rose-50 border-rose-200 text-rose-800 dark:bg-rose-950/40 dark:border-rose-900/50 dark:text-rose-300' 
                            : isSpecial 
                              ? 'bg-amber-50 border-amber-200 text-amber-800 dark:bg-amber-950/40 dark:border-amber-900/50 dark:text-amber-300' 
                              : 'bg-[#002d72]/10 border-[#002d72]/20 text-[#002d72] dark:bg-sky-500/15 dark:border-sky-500/30 dark:text-sky-300'}"
                        >
                          <div class="flex justify-between items-start">
                            <div class="font-black truncate">{course.course_code}</div>
                            <div class="text-[8px] font-bold opacity-60">S{course.section}</div>
                          </div>
                          <!-- Display room name directly inside slot -->
                          <div class="text-[8px] font-bold opacity-70 mt-0.5 truncate flex items-center space-x-0.5">
                            <MapPin size={8} class="shrink-0 text-[#0080c9] dark:text-sky-400" />
                            <span>{course.room_name}</span>
                          </div>
                          <div class="flex justify-between items-center mt-0.5 border-t border-slate-100/50 dark:border-slate-800/50 pt-0.5">
                            <span class="text-[7px] sm:text-[8px] font-bold uppercase opacity-75">{course.slot_type || 'Lecture'}</span>
                            {#if slotCourses.length > 1}
                              <AlertTriangle size={8} class="text-rose-500" />
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

