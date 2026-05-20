<script lang="ts">
  import { onMount } from "svelte";
  import { User, Search, History, BookOpen, Clock, Calendar } from "lucide-svelte";
  import { API_BASE } from "$lib/config";

  let query = $state("");
  let instructors = $state<any[]>([]);
  let selectedInstructor = $state<any>(null);
  let legacyData = $state<any>(null);
  let loading = $state(false);

  async function searchInstructors() {
    if (query.length < 2) {
      instructors = [];
      return;
    }
    const res = await fetch(`${API_BASE}/api/v1/instructors?q=${query}`);
    instructors = await res.json();
  }

  async function selectInstructor(instructor: any) {
    selectedInstructor = instructor;
    instructors = [];
    query = instructor.full_name;
    loading = true;
    try {
      const res = await fetch(`${API_BASE}/api/v1/analytics/instructor/${instructor.id}/legacy`);
      legacyData = await res.json();
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  }

  let timeout: any;
  function handleInput() {
    clearTimeout(timeout);
    timeout = setTimeout(searchInstructors, 300);
  }
</script>

<div class="space-y-8">
  <div>
    <h2 class="text-3xl font-bold text-slate-800 dark:text-slate-100">Instructor DNA</h2>
    <p class="text-slate-500 mt-2 dark:text-slate-400">Historical teaching history and academic footprint.</p>
  </div>

  <!-- Search -->
  <div class="relative max-w-2xl">
    <Search class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
    <input
      type="text"
      bind:value={query}
      oninput={handleInput}
      placeholder="Search for an instructor (e.g. SEMA SAKARYA)..."
      class="w-full pl-12 pr-4 py-4 bg-white border border-slate-200 rounded-xl shadow-sm outline-none focus:ring-2 focus:ring-indigo-500 text-lg dark:bg-slate-900 dark:border-slate-800 dark:text-white"
    />
    
    {#if instructors.length > 0}
      <div class="absolute w-full mt-2 bg-white border border-slate-200 rounded-xl shadow-xl z-20 overflow-hidden dark:bg-slate-900 dark:border-slate-800">
        {#each instructors as inst}
          <button 
            onclick={() => selectInstructor(inst)}
            class="w-full text-left px-6 py-4 hover:bg-slate-50 border-b border-slate-50 last:border-0 flex items-center space-x-3 dark:hover:bg-slate-800/40 dark:border-slate-800"
          >
            <User size={18} class="text-slate-400 dark:text-slate-500" />
            <span class="font-bold text-slate-700 dark:text-slate-300">{inst.full_name}</span>
          </button>
        {/each}
      </div>
    {/if}
  </div>

  {#if loading}
    <div class="flex justify-center py-24">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 dark:border-indigo-500"></div>
    </div>
  {:else if legacyData}
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Stats Summary -->
      <div class="lg:col-span-1 space-y-6">
        <div class="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm space-y-6 dark:bg-slate-900 dark:border-slate-800">
          <div class="flex flex-col items-center text-center">
             <div class="w-20 h-20 bg-indigo-50 dark:bg-indigo-950/40 rounded-full flex items-center justify-center text-indigo-600 dark:text-indigo-400 mb-4">
               <User size={40} />
             </div>
             <h3 class="text-xl font-bold text-slate-800 dark:text-slate-100 leading-tight">{legacyData.instructor_name}</h3>
             <p class="text-sm text-slate-400 font-medium uppercase tracking-widest mt-1">Instructor Legacy</p>
          </div>

          <div class="grid grid-cols-2 gap-4 border-t border-slate-50 dark:border-slate-800/60 pt-6">
            <div class="text-center">
              <div class="text-2xl font-black text-indigo-600 dark:text-indigo-400">{legacyData.total_semesters_taught}</div>
              <div class="text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase">Semesters</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-black text-indigo-600 dark:text-indigo-400">{legacyData.total_courses_taught}</div>
              <div class="text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase">Total Classes</div>
            </div>
          </div>
        </div>

        <!-- Preferred Slots -->
        <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4 dark:bg-slate-900 dark:border-slate-800">
          <h4 class="text-sm font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center space-x-2">
            <Clock size={16} class="text-indigo-500 dark:text-indigo-400" />
            <span>Preferred Slots</span>
          </h4>
          <div class="space-y-2">
            {#each legacyData.preferred_slots as slot}
              <div class="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100 dark:bg-slate-950 dark:border-slate-800/60">
                 <div class="flex items-center space-x-3">
                   <span class="w-8 h-8 bg-white rounded flex items-center justify-center text-xs font-bold border border-slate-200 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-200">{slot.day}</span>
                   <span class="text-sm font-bold text-slate-700 dark:text-slate-300">Hour {slot.hour}</span>
                 </div>
                 <span class="text-xs font-black text-indigo-600 dark:text-indigo-400">{slot.frequency}x</span>
              </div>
            {/each}
          </div>
        </div>
      </div>

      <!-- Teaching History -->
      <div class="lg:col-span-2 space-y-6">
        <div class="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm dark:bg-slate-900 dark:border-slate-800">
          <h4 class="text-sm font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center space-x-2 mb-6">
            <History size={18} class="text-indigo-500 dark:text-indigo-400" />
            <span>Teaching History Timeline</span>
          </h4>
          
          <div class="space-y-4 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
            {#each legacyData.history as item}
              <div class="flex items-start space-x-4 p-4 rounded-xl border border-slate-50 hover:border-indigo-100 hover:bg-indigo-50/30 transition-all dark:border-slate-800/40 dark:hover:border-indigo-950/40 dark:hover:bg-indigo-950/15">
                <div class="text-xs font-black text-indigo-600 bg-white px-3 py-1 rounded-full border border-indigo-100 whitespace-nowrap dark:bg-slate-900 dark:border-indigo-900/40 dark:text-indigo-400">
                  {item.term}
                </div>
                <div class="flex-1">
                  <div class="text-sm font-bold text-slate-800 dark:text-slate-200">{item.course_code}</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{item.title}</div>
                </div>
              </div>
            {/each}
          </div>
        </div>

        <!-- Most Frequent -->
        <div class="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm dark:bg-slate-900 dark:border-slate-800">
           <h4 class="text-sm font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center space-x-2 mb-6">
            <BookOpen size={18} class="text-indigo-500 dark:text-indigo-400" />
            <span>Most Frequent Courses</span>
          </h4>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            {#each Object.entries(legacyData.most_frequent_courses) as [code, count]}
               <div class="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-100 dark:bg-slate-950 dark:border-slate-850">
                  <span class="text-sm font-black text-slate-700 dark:text-slate-350">{code}</span>
                  <div class="flex items-center space-x-2">
                    <div class="text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase">Taught</div>
                    <span class="text-lg font-black text-indigo-600 dark:text-indigo-400">{count}x</span>
                  </div>
               </div>
            {/each}
          </div>
        </div>
      </div>
    </div>
  {/if}
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
