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
  <div class="text-center space-y-3 sm:space-y-4 py-6 sm:py-10">
    <div class="inline-flex p-3 sm:p-3.5 bg-[#002d72]/10 dark:bg-amber-400/10 rounded-2xl text-[#002d72] dark:text-amber-400 mb-1 sm:mb-2">
      <User size={32} class="sm:w-10 sm:h-10" />
    </div>
    <h1 class="font-serif text-2xl sm:text-4xl font-bold text-[#1c1b18] dark:text-neutral-50 tracking-tight">Instructor Archive</h1>
    <p class="font-sans text-[#746f65] max-w-lg mx-auto dark:text-neutral-400 text-xs sm:text-sm px-4">Search and explore the historical teaching footprints and course offerings of Boğaziçi faculty.</p>
  </div>

  <!-- Search -->
  <div class="relative group">
    <Search class="absolute left-4 sm:left-5 top-1/2 -translate-y-1/2 text-[#746f65] group-focus-within:text-[#002d72] dark:group-focus-within:text-amber-400 transition-colors" size={18} />
    <input
      type="text"
      bind:value={query}
      oninput={handleInput}
      placeholder="Search faculty name (e.g. SEMA SAKARYA)..."
      class="w-full pl-11 sm:pl-14 pr-4 sm:pr-6 py-3.5 sm:py-4 bg-[#f7f5ee] border border-[#dbd7cc] rounded-xl shadow-2xs outline-none focus:ring-2 focus:ring-[#c5a059]/20 focus:border-[#c5a059] text-sm sm:text-base transition-all dark:bg-[#18181b] dark:border-[#27272a] dark:text-white dark:focus:border-amber-400"
    />
    
    {#if instructors.length > 0}
      <div class="absolute w-full mt-2 bg-[#f7f5ee] border border-[#dbd7cc] rounded-xl shadow-xl z-50 overflow-hidden dark:bg-[#18181b] dark:border-[#27272a]">
        <div class="p-2.5 border-b border-[#dbd7cc] bg-[#e7e4d9]/50 dark:bg-[#121214] dark:border-[#27272a]">
           <span class="font-mono text-[10px] font-bold text-[#746f65] uppercase tracking-wider px-2">Top Matches ({instructors.length})</span>
        </div>
        <div class="max-h-80 overflow-y-auto custom-scrollbar divide-y divide-[#dbd7cc]/70 dark:divide-[#27272a]">
          {#each instructors as inst}
            <button 
              onclick={() => selectInstructor(inst.id)}
              class="w-full text-left px-4 py-3 hover:bg-[#edeae0] flex items-center justify-between group dark:hover:bg-[#232328] transition-colors cursor-pointer"
            >
              <div class="flex items-center space-x-3">
                <div class="w-8 h-8 bg-[#e7e4d9] rounded-full flex items-center justify-center text-[#746f65] group-hover:bg-[#f7f5ee] dark:bg-[#27272a] dark:text-neutral-400 transition-colors shrink-0">
                   <User size={15} />
                </div>
                <span class="text-sm font-semibold text-[#1c1b18] dark:text-neutral-200 group-hover:text-[#002d72] dark:group-hover:text-amber-400 transition-colors">{inst.full_name}</span>
              </div>
              <ArrowRight size={15} class="text-[#746f65] opacity-60 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all shrink-0" />
            </button>
          {/each}
        </div>
      </div>
    {/if}
  </div>

  <!-- Featured Stats Cards -->
  <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6 pt-4 sm:pt-8">
     <div class="p-5 sm:p-6 bg-[#f7f5ee] rounded-xl border border-[#dbd7cc] shadow-2xs dark:bg-[#18181b] dark:border-[#27272a]">
        <h2 class="font-mono text-[10px] font-bold text-[#746f65] uppercase tracking-wider mb-2">Historical Reach</h2>
        <p class="font-serif text-xl sm:text-2xl font-bold text-[#1c1b18] dark:text-neutral-100">Across 50 years of academic terms and curricular evolution.</p>
     </div>
     <div class="p-5 sm:p-6 bg-[#272521] text-white rounded-xl shadow-2xs dark:bg-[#1f1f23] dark:border dark:border-[#27272a]">
        <h2 class="font-mono text-[10px] font-bold text-amber-300 dark:text-amber-400 uppercase tracking-wider mb-2">Curriculum Coverage</h2>
        <p class="font-serif text-xl sm:text-2xl font-bold">Over 140,000 course records mapped across all faculty rosters.</p>
     </div>
  </div>
</div>
