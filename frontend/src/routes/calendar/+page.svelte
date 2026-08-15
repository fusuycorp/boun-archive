<script lang="ts">
  import { onMount, untrack } from "svelte";
  import { Search, Calendar, Plus, Trash2, AlertTriangle, Filter, Check, X, MapPin } from "lucide-svelte";
  import { API_BASE } from "$lib/config";

  // State
  let terms = $state<any[]>([]);
  let selectedTerm = $state("");
  let searchQuery = $state("");
  let searchResults = $state<any[]>([]);
  let myCourses = $state<any[]>([]);
  let loading = $state(false);
  let days = ["M", "T", "W", "Th", "F", "St", "Su"];
  let hours = Array.from({ length: 14 }, (_, i) => i + 1);

  // Commute Config State
  let commuteStrictness = $state("all"); // "all", "high", "impossible", "none"

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
    const res = await fetch(`${API_BASE}/v1/terms`);
    terms = await res.json();
    if (terms.length > 0) {
      selectedTerm = terms[0].id;
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
      const data = await res.json();
      searchResults = data.hits;
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

  // Helper to resolve campus based on room name prefixes
  function resolveCampus(roomName: string): string {
    if (!roomName) return "Unknown";
    const name = roomName.trim().toUpperCase();
    if (name.startsWith("TB") || name.startsWith("IB") || name.startsWith("OD") || name.startsWith("DODGE") || name.startsWith("BTS") || name.startsWith("ALBERT") || name.startsWith("JF")) {
      return "South";
    } else if (name.startsWith("KB") || name.startsWith("NH") || name.startsWith("ETA") || name.startsWith("BM") || name.startsWith("BİM") || name.startsWith("BIM") || name.startsWith("EF") || name.startsWith("M ") || name.startsWith("M-")) {
      return "North";
    } else if (name.startsWith("HB") || name.startsWith("HC") || name.startsWith("HD") || name.startsWith("HK")) {
      return "Hisar";
    } else if (name.startsWith("KP") || name.startsWith("KYD") || name.startsWith("KİLYOS") || name.startsWith("KILYOS") || name.startsWith("SARITEPE") || name.startsWith("SARI")) {
      return "Kilyos";
    } else {
      if (name.includes("KILYOS") || name.includes("SARITEPE")) return "Kilyos";
      if (name.includes("HISAR") || name.includes("HİSAR")) return "Hisar";
      if (name.length > 1 && name.startsWith("M") && ((name[1] >= "0" && name[1] <= "9") || name[1] === " ")) return "North";
      return "South";
    }
  }

  // Conflict Logic
  function getCoursesAt(day: string, hour: number) {
    return myCourses.flatMap(c => 
      c.slots
        .filter((s: any) => s.day_code === day && s.slot_hour === hour)
        .map((s: any) => ({ ...c, slot_type: s.slot_title || "", room_name: s.room_name || "N/A" }))
    );
  }

  function isLabOrPS(slotType: string) {
    if (!slotType) return false;
    const type = slotType.toLowerCase();
    return type.includes("lab") || type.includes("ps") || type.includes("practice");
  }

  // Dash of Death - Campus Commute Warning Analyser
  const commuteWarnings = $derived.by(() => {
    const warnings: any[] = [];
    if (commuteStrictness === "none") return warnings;

    days.forEach(day => {
      for (let i = 0; i < hours.length - 1; i++) {
        const h1 = hours[i];
        const h2 = hours[i + 1];

        const courses1 = getCoursesAt(day, h1);
        const courses2 = getCoursesAt(day, h2);

        if (courses1.length > 0 && courses2.length > 0) {
          courses1.forEach(c1 => {
            courses2.forEach(c2 => {
              const camp1 = resolveCampus(c1.room_name);
              const camp2 = resolveCampus(c2.room_name);

              if (camp1 !== camp2 && camp1 !== "Unknown" && camp2 !== "Unknown") {
                let risk = "Medium";
                let description = "10 min steep walk";

                if (camp1 === "Kilyos" || camp2 === "Kilyos") {
                  risk = "Impossible";
                  description = "requires intercampus travel (Kilyos Prep to South/North)";
                } else if ((camp1 === "Hisar" || camp2 === "Hisar") && (camp1 === "South" || camp2 === "South" || camp1 === "North" || camp2 === "North")) {
                  risk = "High";
                  description = "requires crossing busy highways (Hisar to South/North)";
                }

                const meetsStrictness = 
                  commuteStrictness === "all" ||
                  (commuteStrictness === "high" && (risk === "High" || risk === "Impossible")) ||
                  (commuteStrictness === "impossible" && risk === "Impossible");

                if (meetsStrictness) {
                  warnings.push({
                    day,
                    hour1: h1,
                    hour2: h2,
                    code1: c1.course_code,
                    code2: c2.course_code,
                    room1: c1.room_name,
                    room2: c2.room_name,
                    camp1,
                    camp2,
                    risk,
                    description
                  });
                }
              }
            });
          });
        }
      }
    });
    return warnings;
  });

  onMount(fetchTerms);

  let timeout: any;
  function handleInput() {
    clearTimeout(timeout);
    timeout = setTimeout(performSearch, 300);
  }
</script>

<div class="space-y-6 h-full flex flex-col">
  <div class="flex items-center justify-between shrink-0">
    <div>
      <h2 class="text-3xl font-bold text-slate-800 dark:text-slate-100">Weekly Planner</h2>
      <p class="text-slate-500 mt-2 dark:text-slate-400">Personalize your academic schedule and resolve conflicts.</p>
    </div>
    
    <div class="flex items-center space-x-4">
      <div class="flex flex-col space-y-1">
        <label class="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest px-1">Selected Semester</label>
        <select 
          bind:value={selectedTerm} 
          class="min-w-[200px] p-2 bg-white border border-slate-200 rounded-xl text-sm font-bold text-slate-700 outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-200"
        >
          {#each terms as term}
            <option value={term.id}>{term.id}</option>
          {/each}
        </select>
      </div>
    </div>
  </div>

  <div class="flex-1 flex gap-6 min-h-0">
    <!-- Left Sidebar: Search & List -->
    <aside class="w-80 flex flex-col space-y-4 shrink-0 overflow-y-auto pr-2 custom-scrollbar">
      <!-- Search Box -->
      <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm space-y-4 dark:bg-slate-900 dark:border-slate-800">
        <div class="relative">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
          <input 
            type="text" 
            bind:value={searchQuery}
            oninput={handleInput}
            placeholder="Find a course..."
            class="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-100 rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-slate-950 dark:border-slate-800 dark:text-white"
          />
        </div>

        {#if searchResults.length > 0}
          <div class="space-y-2 max-h-60 overflow-y-auto pr-1 custom-scrollbar">
            {#each searchResults as course}
              {@const isAdded = myCourses.some(c => c.id === course.id)}
              <button 
                onclick={() => toggleCourse(course.id)}
                class="w-full p-3 border rounded-xl text-left transition-all group
                {isAdded 
                  ? 'bg-indigo-50 border-indigo-200 ring-2 ring-indigo-500/10 dark:bg-indigo-950/40 dark:border-indigo-900/50 dark:ring-indigo-500/20' 
                  : 'bg-slate-50 border-slate-100 hover:bg-indigo-50 hover:border-indigo-200 dark:bg-slate-950 dark:border-slate-800 dark:hover:bg-indigo-950/20 dark:hover:border-indigo-900/40'}"
              >
                <div class="flex justify-between items-start">
                  <div class="flex items-center space-x-2">
                    <span class="text-xs font-black text-indigo-600 dark:text-indigo-400 uppercase">{course.course_code}</span>
                    <span class="text-[10px] text-slate-400 dark:text-slate-500 font-bold">Sec {course.section}</span>
                  </div>
                  {#if isAdded}
                    <div class="w-5 h-5 bg-indigo-600 rounded-full flex items-center justify-center text-white shadow-sm">
                       <Check size={12} strokeWidth={4} />
                    </div>
                  {:else}
                    <Plus size={14} class="text-slate-300 group-hover:text-indigo-600 dark:text-slate-650 dark:group-hover:text-indigo-400" />
                  {/if}
                </div>
                <div class="text-xs font-bold text-slate-700 dark:text-slate-300 mt-1 line-clamp-1">{course.title}</div>
              </button>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Config Panel for Commutes -->
      <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm space-y-3 dark:bg-slate-900 dark:border-slate-800">
        <label class="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest px-1">Commute Warnings</label>
        <select 
          bind:value={commuteStrictness}
          class="w-full p-2 bg-slate-50 border border-slate-100 rounded-xl text-xs font-bold text-slate-700 outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-slate-950 dark:border-slate-800 dark:text-slate-200"
        >
          <option value="all">Show All (Incl. South-to-North)</option>
          <option value="high">High Risk Only (Hisar crossings)</option>
          <option value="impossible">Impossible Only (Kilyos travel)</option>
          <option value="none">Disable warnings</option>
        </select>
      </div>

      <!-- Commute Warnings Panel -->
      {#if commuteWarnings.length > 0}
        <div class="bg-amber-50 border border-amber-200 p-4 rounded-2xl shadow-sm space-y-3 dark:bg-amber-950/20 dark:border-amber-900/50">
          <div class="flex items-center space-x-2 text-amber-700 dark:text-amber-400 font-black text-xs uppercase tracking-wider">
            <AlertTriangle size={16} />
            <span>Dash of Death warnings</span>
          </div>
          <div class="space-y-2.5 max-h-48 overflow-y-auto pr-1 custom-scrollbar">
            {#each commuteWarnings as w}
              <div class="bg-white p-2.5 rounded-xl border border-amber-100 dark:bg-slate-950 dark:border-amber-950/40 text-[10px] space-y-1">
                <div class="flex justify-between items-center font-bold">
                  <span class="text-amber-600 dark:text-amber-400">{w.day} - Hour {w.hour1} to {w.hour2}</span>
                  <span class="px-1.5 py-0.5 rounded text-[8px] font-black uppercase
                    {w.risk === 'Impossible' ? 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400' : 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400'}">
                    {w.risk} Risk
                  </span>
                </div>
                <p class="text-slate-600 dark:text-slate-400 leading-tight">
                  <span class="font-black text-slate-700 dark:text-slate-300">{w.code1}</span> ({w.room1}, {w.camp1} Campus) to 
                  <span class="font-black text-slate-700 dark:text-slate-300">{w.code2}</span> ({w.room2}, {w.camp2} Campus).
                </p>
                <div class="text-[9px] font-semibold text-slate-400 italic mt-0.5">{w.description}</div>
              </div>
            {/each}
          </div>
        </div>
      {/if}

      <!-- Selected List -->
      <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex-1 space-y-4 dark:bg-slate-900 dark:border-slate-800">
        <h3 class="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest px-1">My Courses ({myCourses.length})</h3>
        <div class="space-y-2">
          {#each myCourses as course}
            <div class="p-3 bg-white border border-slate-100 rounded-xl group relative dark:bg-slate-950 dark:border-slate-800/80">
              <div class="flex items-center space-x-2">
                <div class="text-xs font-black text-indigo-600 dark:text-indigo-400 uppercase">{course.course_code}</div>
                <div class="text-[10px] text-slate-400 dark:text-slate-500 font-bold">Section {course.section}</div>
              </div>
              <div class="text-xs font-bold text-slate-700 dark:text-slate-300 mt-1">{course.title}</div>
              <button 
                onclick={() => removeCourse(course.id)}
                class="absolute top-2 right-2 p-1.5 opacity-0 group-hover:opacity-100 transition-opacity text-red-500 hover:bg-red-50 dark:hover:bg-red-950/40 rounded"
              >
                <Trash2 size={14} />
              </button>
            </div>
          {/each}
          {#if myCourses.length === 0}
            <div class="text-center py-12 text-slate-300 dark:text-slate-600">
              <Calendar size={32} class="mx-auto mb-2 opacity-20" />
              <p class="text-xs font-medium">Your planner is empty</p>
            </div>
          {/if}
        </div>
      </div>
    </aside>

    <!-- Main Calendar Grid -->
    <div class="flex-1 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col min-w-0 dark:bg-slate-900 dark:border-slate-800">
      <div class="overflow-auto flex-1 custom-scrollbar">
        <table class="w-full border-collapse table-fixed">
          <thead class="sticky top-0 z-10 bg-slate-50 border-b border-slate-200 dark:bg-slate-950 dark:border-slate-800">
            <tr>
              <th class="p-3 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest w-16 border-r border-slate-200 dark:border-slate-800">Hr</th>
              {#each days as day}
                <th class="p-3 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">{day}</th>
              {/each}
            </tr>
          </thead>
          <tbody>
            {#each hours as hour}
              <tr class="border-b border-slate-100 last:border-0 dark:border-slate-800/60">
                <td class="p-2 text-center text-xs font-black text-slate-300 dark:text-slate-600 border-r border-slate-200 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-950/20">{hour}</td>
                {#each days as day}
                  {@const slotCourses = getCoursesAt(day, hour)}
                  <td class="p-1 h-24 vertical-align-top relative">
                    <div class="flex flex-col gap-1 h-full font-sans">
                      {#each slotCourses as course}
                        {@const isSpecial = isLabOrPS(course.slot_type)}
                        <div 
                          class="p-1.5 rounded-lg border text-[10px] leading-tight flex-1 flex flex-col justify-center
                          {slotCourses.length > 1 
                            ? 'bg-red-50 border-red-200 text-red-700 dark:bg-red-950/40 dark:border-red-900/50 dark:text-red-400' 
                            : isSpecial 
                              ? 'bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-950/40 dark:border-amber-900/50 dark:text-amber-400' 
                              : 'bg-indigo-50 border-indigo-200 text-indigo-700 dark:bg-indigo-950/40 dark:border-indigo-900/50 dark:text-indigo-300'}"
                        >
                          <div class="flex justify-between items-start">
                            <div class="font-black truncate">{course.course_code}</div>
                            <div class="text-[8px] font-bold opacity-60">Sec {course.section}</div>
                          </div>
                          <!-- Display room name directly inside slot -->
                          <div class="text-[8px] font-bold opacity-70 mt-0.5 truncate flex items-center space-x-0.5">
                            <MapPin size={8} class="shrink-0 text-indigo-500" />
                            <span>{course.room_name}</span>
                          </div>
                          <div class="flex justify-between items-center mt-0.5 border-t border-slate-100/50 dark:border-slate-850/50 pt-0.5">
                            <span class="text-[8px] font-bold uppercase opacity-75">{course.slot_type || 'Lecture'}</span>
                            {#if slotCourses.length > 1}
                              <AlertTriangle size={8} class="text-red-500" />
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

