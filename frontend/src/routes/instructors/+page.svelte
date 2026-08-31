<script lang="ts">
  import { User, Search, History, BookOpen, Clock, Calendar, ArrowRight } from "lucide-svelte";
  import { API_BASE } from "$lib/config";
  import { goto } from "$app/navigation";
  import type { Instructor } from "$lib/types";
  import type { PageData } from "./$types";

  let { data }: { data: PageData } = $props();

  let query = $state("");
  let instructors = $state<Instructor[]>([]);
  let loading = $state(false);

  async function searchInstructors() {
    if (query.length < 2) {
      instructors = [];
      return;
    }
    loading = true;
    try {
      const res = await fetch(`${API_BASE}/v1/instructors?q=${encodeURIComponent(query)}`);
      if (res.ok) {
        instructors = await res.json();
      }
    } catch (e) {
      console.error("Failed to search instructors", e);
    } finally {
      loading = false;
    }
  }

  function selectInstructor(id: number) {
    goto(`/instructor/${id}`);
  }

  import { onMount } from "svelte";
  import { page } from "$app/state";

  let timeout: ReturnType<typeof setTimeout> | undefined;
  function handleInput() {
    clearTimeout(timeout);
    timeout = setTimeout(searchInstructors, 300);
  }

  onMount(() => {
    const qParam = page.url.searchParams.get("q");
    if (qParam) {
      query = qParam;
      searchInstructors();
    }
  });
</script>

<div class="space-y-6 sm:space-y-8 max-w-4xl mx-auto">
  <div class="text-center space-y-3 sm:space-y-4 py-6 sm:py-10">
    <div class="inline-flex p-3 sm:p-3.5 bg-[#002d72]/10 dark:bg-[#8cc8ea]/15 rounded-2xl text-[#002d72] dark:text-[#8cc8ea] mb-1 sm:mb-2">
      <User size={32} class="sm:w-10 sm:h-10" />
    </div>
    <h1 class="font-serif text-2xl sm:text-4xl font-bold text-[#002d72] dark:text-slate-50 tracking-tight">Instructor Archive</h1>
    <p class="font-sans text-[#525f7f] max-w-lg mx-auto dark:text-slate-400 text-xs sm:text-sm px-4">Search and explore the historical teaching footprints and course offerings of Boğaziçi faculty.</p>
  </div>

  <!-- Search -->
  <div class="relative group">
    <Search class="absolute left-4 sm:left-5 top-1/2 -translate-y-1/2 text-[#525f7f] group-focus-within:text-[#002d72] dark:group-focus-within:text-[#8cc8ea] transition-colors" size={18} />
    <input
      type="text"
      bind:value={query}
      oninput={handleInput}
      placeholder="Search faculty name (e.g. SEMA SAKARYA)..."
      class="w-full pl-11 sm:pl-14 pr-4 sm:pr-6 py-3.5 sm:py-4 bg-white border border-[#e5e0d8] rounded-xl shadow-2xs outline-none focus:ring-2 focus:ring-[#002d72]/20 focus:border-[#002d72] text-sm sm:text-base transition-all dark:bg-[#121827] dark:border-[#1e293b] dark:text-white dark:focus:border-[#8cc8ea] dark:focus:ring-[#8cc8ea]/20"
    />
    
    {#if instructors.length > 0}
      <div class="absolute w-full mt-2 bg-white border border-[#e5e0d8] rounded-xl shadow-xl z-50 overflow-hidden dark:bg-[#121827] dark:border-[#1e293b]">
        <div class="p-2.5 border-b border-[#e5e0d8] bg-[#f3efe6]/60 dark:bg-[#0a0e1a] dark:border-[#1e293b]">
           <span class="font-mono text-[10px] font-bold text-[#525f7f] uppercase tracking-wider px-2">Top Matches ({instructors.length})</span>
        </div>
        <div class="max-h-80 overflow-y-auto custom-scrollbar divide-y divide-[#e5e0d8] dark:divide-[#1e293b]">
          {#each instructors as inst}
            <button 
              onclick={() => selectInstructor(inst.id)}
              class="w-full text-left px-4 py-3 hover:bg-[#f3efe6]/50 flex items-center justify-between group dark:hover:bg-slate-800/50 transition-colors cursor-pointer"
            >
              <div class="flex items-center space-x-3">
                <div class="w-8 h-8 bg-[#f3efe6] rounded-full flex items-center justify-center text-[#525f7f] group-hover:bg-[#002d72]/10 group-hover:text-[#002d72] dark:bg-slate-800 dark:text-slate-400 dark:group-hover:bg-[#8cc8ea]/15 dark:group-hover:text-[#8cc8ea] transition-colors shrink-0">
                   <User size={15} />
                </div>
                <span class="text-sm font-semibold text-[#161e2e] dark:text-slate-200 group-hover:text-[#002d72] dark:group-hover:text-[#8cc8ea] transition-colors">{inst.full_name}</span>
              </div>
              <ArrowRight size={15} class="text-[#525f7f] opacity-60 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all shrink-0" />
            </button>
          {/each}
        </div>
      </div>
    {/if}
  </div>

  <!-- Featured Stats Cards -->
  <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6 pt-4 sm:pt-8">
     <div class="p-5 sm:p-6 bg-white rounded-xl border border-[#e5e0d8] shadow-2xs dark:bg-[#121827] dark:border-[#1e293b]">
        <h2 class="font-mono text-[10px] font-bold text-[#525f7f] uppercase tracking-wider mb-2">Historical Reach</h2>
        <p class="font-serif text-xl sm:text-2xl font-bold text-[#002d72] dark:text-slate-100">Across 50 years of academic terms and curricular evolution.</p>
     </div>
     <div class="p-5 sm:p-6 bg-[#001b44] text-white rounded-xl shadow-2xs dark:bg-[#0a0e1a] dark:border dark:border-[#1e293b]">
        <h2 class="font-mono text-[10px] font-bold text-[#8cc8ea] uppercase tracking-wider mb-2">Curriculum Coverage</h2>
        <p class="font-serif text-xl sm:text-2xl font-bold">Over 140,000 course records mapped across all faculty rosters.</p>
     </div>
  </div>
</div>
