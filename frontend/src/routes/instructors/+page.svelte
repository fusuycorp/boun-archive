<script lang="ts">
  import { onMount } from "svelte";
  import { User, Search, History, BookOpen, Clock, Calendar, ArrowRight } from "lucide-svelte";
  import { API_BASE } from "$lib/config";
  import { goto } from "$app/navigation";

  let query = $state("");
  let instructors = $state<any[]>([]);
  let loading = $state(false);

  async function searchInstructors() {
    if (query.length < 2) {
      instructors = [];
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/v1/instructors?q=${encodeURIComponent(query)}`);
      if (res.ok) {
        instructors = await res.json();
      }
    } catch (e) {
      console.error("Failed to search instructors", e);
    }
  }

  function selectInstructor(id: number) {
    goto(`/instructor/${id}`);
  }

  let timeout: any;
  function handleInput() {
    clearTimeout(timeout);
    timeout = setTimeout(searchInstructors, 300);
  }
</script>

<div class="space-y-6 sm:space-y-8 max-w-4xl mx-auto">
  <div class="text-center space-y-3 sm:space-y-4 py-6 sm:py-12">
    <div class="inline-flex p-3 sm:p-4 bg-[#002d72]/10 dark:bg-sky-500/15 rounded-3xl text-[#002d72] dark:text-sky-400 mb-1 sm:mb-2">
      <User size={36} class="sm:w-12 sm:h-12" />
    </div>
    <h2 class="text-2xl sm:text-4xl font-black text-slate-800 dark:text-slate-100 tracking-tight">Instructor Archive</h2>
    <p class="text-slate-500 max-w-lg mx-auto dark:text-slate-400 font-medium text-xs sm:text-base px-4">Search and explore the historical teaching history and academic footprints of Bogazici faculty.</p>
  </div>

  <!-- Search -->
  <div class="relative group">
    <Search class="absolute left-4 sm:left-6 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#0080c9] dark:group-focus-within:text-sky-400 transition-colors" size={20} />
    <input
      type="text"
      bind:value={query}
      oninput={handleInput}
      placeholder="Search instructor (e.g. SEMA SAKARYA)..."
      class="w-full pl-12 sm:pl-16 pr-4 sm:pr-6 py-4 sm:py-5 bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl shadow-2xs outline-none focus:ring-4 focus:ring-[#0080c9]/10 focus:border-[#0080c9] text-base sm:text-xl transition-all dark:bg-[#0f172a] dark:border-slate-800/80 dark:text-white dark:focus:border-sky-400"
    />
    
    {#if instructors.length > 0}
      <div class="absolute w-full mt-2 sm:mt-4 bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl shadow-2xl z-50 overflow-hidden dark:bg-[#0f172a] dark:border-slate-800/80">
        <div class="p-3 border-b border-slate-50 bg-slate-50/50 dark:bg-slate-950/50 dark:border-slate-800">
           <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest px-3">Top Matches ({instructors.length})</span>
        </div>
        <div class="max-h-80 overflow-y-auto custom-scrollbar">
          {#each instructors as inst}
            <button 
              onclick={() => selectInstructor(inst.id)}
              class="w-full text-left px-4 sm:px-6 py-3.5 sm:py-4 hover:bg-[#002d72]/5 border-b border-slate-50 last:border-0 flex items-center justify-between group dark:hover:bg-sky-500/10 dark:border-slate-800/80 transition-colors cursor-pointer"
            >
              <div class="flex items-center space-x-3 sm:space-x-4">
                <div class="w-8 sm:w-10 h-8 sm:h-10 bg-slate-100 rounded-full flex items-center justify-center text-slate-400 group-hover:bg-white dark:bg-slate-800 dark:text-slate-600 transition-colors shrink-0">
                   <User size={18} />
                </div>
                <span class="text-sm sm:text-base font-bold text-slate-700 dark:text-slate-200 group-hover:text-[#002d72] dark:group-hover:text-sky-300 transition-colors">{inst.full_name}</span>
              </div>
              <ArrowRight size={18} class="text-slate-300 opacity-60 sm:opacity-0 group-hover:opacity-100 -translate-x-2 sm:-translate-x-4 group-hover:translate-x-0 transition-all shrink-0" />
            </button>
          {/each}
        </div>
      </div>
    {/if}
  </div>

  <!-- Featured Stats Cards -->
  <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6 pt-6 sm:pt-12">
     <div class="p-5 sm:p-8 bg-white rounded-2xl sm:rounded-3xl border border-slate-200/80 shadow-2xs dark:bg-[#0f172a] dark:border-slate-800/80">
        <h4 class="text-xs sm:text-sm font-black text-slate-400 uppercase tracking-widest mb-2 sm:mb-4">Historical Reach</h4>
        <p class="text-xl sm:text-2xl font-bold text-slate-800 dark:text-slate-100">Across 50 years of academic cycles.</p>
     </div>
     <div class="p-5 sm:p-8 bg-[#002d72] rounded-2xl sm:rounded-3xl text-white shadow-md dark:shadow-none">
        <h4 class="text-xs sm:text-sm font-black text-sky-200 uppercase tracking-widest mb-2 sm:mb-4">Data Coverage</h4>
        <p class="text-xl sm:text-2xl font-bold">140,000+ course instances mapped to instructors.</p>
     </div>
  </div>
</div>
