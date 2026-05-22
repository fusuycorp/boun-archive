<script lang="ts">
  import { onMount } from "svelte";
  import { Search, Calendar, Plus, Trash2, AlertTriangle, Filter, Check, X } from "lucide-svelte";
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

  // Persistence
  $effect(() => {
    if (selectedTerm) {
      const saved = localStorage.getItem(`planner_${selectedTerm}`);
      if (saved) {
        myCourses = JSON.parse(saved);
      } else {
        myCourses = [];
      }
    }
  });

  $effect(() => {
    if (selectedTerm) {
      localStorage.setItem(`planner_${selectedTerm}`, JSON.stringify(myCourses));
    }
  });

  async function fetchTerms() {
    const res = await fetch(`${API_BASE}/api/v1/terms`);
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
      const res = await fetch(`${API_BASE}/api/v1/search?${params.toString()}`);
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
      const res = await fetch(`${API_BASE}/api/v1/courses/${courseId}`);
      const course = await res.json();
      myCourses = [...myCourses, course];
    }
  }

  function removeCourse(id: number) {
    myCourses = myCourses.filter(c => c.id !== id);
  }

  // Conflict Logic
  function getCoursesAt(day: string, hour: number) {
    return myCourses.flatMap(c => 
      c.slots
        .filter((s: any) => s.day_code === day && s.slot_hour === hour)
        .map((s: any) => ({ ...c, slot_type: s.slot_title || "" }))
    );
  }

  // Check if slot type is lab or ps
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
          <div class="space-y-2">
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
                  <td class="p-1 h-20 vertical-align-top relative">
                    <div class="flex flex-col gap-1 h-full font-sans">
                      {#each slotCourses as course}
                        {@const isSpecial = isLabOrPS(course.slot_type)}
                        <div 
                          class="p-1.5 rounded-lg border text-[10px] leading-tight flex-1 flex flex-col justify-center
                          {slotCourses.length > 1 
                            ? 'bg-red-50 border-red-200 text-red-700 dark:bg-red-950/40 dark:border-red-900/50 dark:text-red-455' 
                            : isSpecial 
                              ? 'bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-950/40 dark:border-amber-900/50 dark:text-amber-400' 
                              : 'bg-indigo-50 border-indigo-200 text-indigo-700 dark:bg-indigo-950/40 dark:border-indigo-900/50 dark:text-indigo-300'}"
                        >
                          <div class="flex justify-between items-start">
                            <div class="font-black truncate">{course.course_code}</div>
                            <div class="text-[8px] font-bold opacity-60">Sec {course.section}</div>
                          </div>
                          <div class="flex justify-between items-center mt-0.5">
                            <span class="text-[8px] font-bold uppercase opacity-70">{course.slot_type || 'Lecture'}</span>
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

<style>
  .custom-scrollbar::-webkit-scrollbar {
    width: 6px;
    height: 6px;
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
