<script lang="ts">
  import { onMount } from "svelte";
  import { Search, Filter, BookOpen, User, Calendar, MapPin, Check, X } from "lucide-svelte";

  let query = $state("");
  let results = $state<any[]>([]);
  let currentFacets = $state<any>({});
  let globalFacets = $state<any>({});
  let loading = $state(false);
  let totalHits = $state(0);
  let offset = $state(0);
  const limit = 20;

  // Filters
  let selectedTerms = $state<string[]>([]);
  let selectedDepts = $state<string[]>([]);
  let deptSearch = $state("");

  async function fetchGlobalFacets() {
    try {
      const response = await fetch("http://localhost:8000/api/v1/facets");
      globalFacets = await response.json();
    } catch (e) {
      console.error("Failed to fetch facets", e);
    }
  }

  async function performSearch(resetOffset = true) {
    loading = true;
    if (resetOffset) offset = 0;
    
    try {
      const params = new URLSearchParams();
      params.append("q", query);
      params.append("limit", limit.toString());
      params.append("offset", offset.toString());
      
      selectedTerms.forEach(t => params.append("term", t));
      selectedDepts.forEach(d => params.append("dept", d));

      const response = await fetch(`http://localhost:8000/api/v1/search?${params.toString()}`);
      const data = await response.json();
      results = data.hits;
      currentFacets = data.facetDistribution;
      // Meilisearch returns totalHits or estimatedTotalHits depending on configuration
      totalHits = data.totalHits ?? data.estimatedTotalHits ?? 0;
    } catch (e) {
      console.error("Search failed", e);
    } finally {
      loading = false;
    }
  }

  function handlePageChange(newOffset: number) {
    offset = newOffset;
    performSearch(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function toggleTerm(term: string) {
    if (selectedTerms.includes(term)) {
      selectedTerms = selectedTerms.filter(t => t !== term);
    } else {
      selectedTerms = [...selectedTerms, term];
    }
    performSearch();
  }

  function toggleDept(dept: string) {
    if (selectedDepts.includes(dept)) {
      selectedDepts = selectedDepts.filter(d => d !== dept);
    } else {
      selectedDepts = [...selectedDepts, dept];
    }
    performSearch();
  }

  function clearFilters() {
    selectedTerms = [];
    selectedDepts = [];
    query = "";
    performSearch();
  }

  // Debounced search
  let timeout: any;
  function handleInput() {
    clearTimeout(timeout);
    timeout = setTimeout(performSearch, 300);
  }

  onMount(() => {
    fetchGlobalFacets();
    performSearch();
  });

  const filteredDepts = $derived(
    globalFacets.dept_code 
      ? Object.keys(globalFacets.dept_code)
          .sort()
          .filter(d => d.toLowerCase().includes(deptSearch.toLowerCase()))
      : []
  );
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <h2 class="text-3xl font-bold text-slate-800 dark:text-slate-100">Course Search</h2>
    <div class="flex items-center space-x-4">
       {#if selectedTerms.length > 0 || selectedDepts.length > 0 || query}
          <button 
            onclick={clearFilters}
            class="text-xs font-bold text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-300 flex items-center space-x-1 bg-indigo-50 dark:bg-indigo-950/40 px-3 py-1.5 rounded-full transition-colors"
          >
            <X size={14} />
            <span>Clear All</span>
          </button>
       {/if}
       <div class="text-sm text-slate-500 font-medium bg-white px-3 py-1.5 rounded-full border border-slate-200 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-400">
         {totalHits.toLocaleString()} results found
       </div>
    </div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-4 gap-8">
    <!-- Sidebar Filters -->
    <aside class="space-y-6">
      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden sticky top-24 dark:bg-slate-900 dark:border-slate-800">
        <div class="p-5 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between dark:border-slate-800 dark:bg-slate-950/50">
          <div class="flex items-center space-x-2 text-slate-700 dark:text-slate-300 font-bold">
            <Filter size={18} />
            <span>Filters</span>
          </div>
        </div>

        <div class="p-5 space-y-8 max-h-[calc(100vh-200px)] overflow-y-auto custom-scrollbar">
          <!-- Term Filter -->
          <div class="space-y-3">
            <label class="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center justify-between">
              <span>Academic Term</span>
              <span class="text-indigo-500 dark:text-indigo-400">{selectedTerms.length || ''}</span>
            </label>
            <div class="space-y-1 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
              {#if globalFacets.term}
                {#each Object.keys(globalFacets.term).sort().reverse() as term}
                  <button 
                    onclick={() => toggleTerm(term)}
                    class="w-full flex items-center justify-between p-2 rounded-lg text-sm transition-all
                    {selectedTerms.includes(term) 
                      ? 'bg-indigo-50 text-indigo-700 font-bold dark:bg-indigo-950/40 dark:text-indigo-400' 
                      : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/40'}"
                  >
                    <div class="flex items-center space-x-2">
                      <div class="w-4 h-4 rounded border flex items-center justify-center transition-colors
                        {selectedTerms.includes(term) 
                          ? 'bg-indigo-600 border-indigo-600 dark:bg-indigo-500 dark:border-indigo-500' 
                          : 'bg-white border-slate-300 dark:bg-slate-800 dark:border-slate-700'}">
                        {#if selectedTerms.includes(term)}
                          <Check size={12} class="text-white" />
                        {/if}
                      </div>
                      <span class="truncate">{term}</span>
                    </div>
                    <span class="text-[10px] opacity-50 font-mono">
                       {currentFacets.term?.[term] ?? 0}
                    </span>
                  </button>
                {/each}
              {/if}
            </div>
          </div>

          <!-- Department Filter -->
          <div class="space-y-3">
            <label class="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center justify-between">
              <span>Department</span>
              <span class="text-indigo-500 dark:text-indigo-400">{selectedDepts.length || ''}</span>
            </label>
            
            <div class="relative">
              <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" size={12} />
              <input 
                type="text" 
                bind:value={deptSearch}
                placeholder="Filter departments..."
                class="w-full pl-8 pr-2 py-1.5 bg-slate-50 border border-slate-100 rounded-md text-xs outline-none focus:ring-1 focus:ring-indigo-500 dark:bg-slate-950 dark:border-slate-800 dark:text-slate-200"
              />
            </div>

            <div class="space-y-1 max-h-64 overflow-y-auto pr-2 custom-scrollbar">
              {#each filteredDepts as dept}
                <button 
                  onclick={() => toggleDept(dept)}
                  class="w-full flex items-center justify-between p-2 rounded-lg text-sm transition-all
                  {selectedDepts.includes(dept) 
                    ? 'bg-indigo-50 text-indigo-700 font-bold dark:bg-indigo-950/40 dark:text-indigo-400' 
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/40'}"
                >
                  <div class="flex items-center space-x-2">
                    <div class="w-4 h-4 rounded border flex items-center justify-center transition-colors
                      {selectedDepts.includes(dept) 
                        ? 'bg-indigo-600 border-indigo-600 dark:bg-indigo-500 dark:border-indigo-500' 
                        : 'bg-white border-slate-300 dark:bg-slate-800 dark:border-slate-700'}">
                      {#if selectedDepts.includes(dept)}
                        <Check size={12} class="text-white" />
                      {/if}
                    </div>
                    <span class="truncate">{dept}</span>
                  </div>
                  <span class="text-[10px] opacity-50 font-mono">
                    {currentFacets.dept_code?.[dept] ?? 0}
                  </span>
                </button>
              {/each}
            </div>
          </div>
        </div>
      </div>
    </aside>

    <!-- Search Results -->
    <div class="lg:col-span-3 space-y-6">
      <div class="relative group">
        <Search class="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-indigo-500 dark:group-focus-within:text-indigo-400 transition-colors" size={24} />
        <input
          type="text"
          bind:value={query}
          oninput={handleInput}
          placeholder="Search 140,000+ historical courses..."
          class="w-full pl-14 pr-6 py-5 bg-white border border-slate-200 rounded-2xl shadow-sm outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 text-xl transition-all dark:bg-slate-900 dark:border-slate-800 dark:text-white dark:focus:border-indigo-500 dark:focus:ring-indigo-500/20"
        />
      </div>

      {#if loading}
        <div class="flex flex-col items-center justify-center py-24 space-y-4">
          <div class="animate-spin rounded-full h-12 w-12 border-4 border-slate-100 border-t-indigo-600 dark:border-slate-800 dark:border-t-indigo-500"></div>
          <p class="text-slate-500 dark:text-slate-400 font-medium animate-pulse">Querying Meilisearch...</p>
        </div>
      {:else}
        <div class="grid grid-cols-1 gap-4">
          {#each results as course}
            <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md hover:border-indigo-300 transition-all group dark:bg-slate-900 dark:border-slate-800 dark:hover:border-indigo-500/50">
              <div class="flex justify-between items-start">
                <div class="space-y-2">
                  <div class="flex items-center space-x-2">
                    <span class="px-2.5 py-1 bg-indigo-50 text-indigo-700 text-[10px] font-black rounded-lg uppercase tracking-wider border border-indigo-100 dark:bg-indigo-950/40 dark:text-indigo-400 dark:border-indigo-900/50">{course.course_code}</span>
                    <span class="text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-widest">Section {course.section}</span>
                  </div>
                  <h3 class="text-xl font-bold text-slate-800 dark:text-slate-100 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors leading-tight">{course.title}</h3>
                </div>
                <div class="text-right flex flex-col items-end">
                  <div class="text-sm font-black text-slate-700 dark:text-slate-300">{course.credits} <span class="text-[10px] text-slate-400 dark:text-slate-500 font-normal uppercase">Credits</span></div>
                  <div class="text-xs text-slate-400 dark:text-slate-500 font-bold">{course.ects} <span class="font-normal uppercase">ECTS</span></div>
                </div>
              </div>

              <div class="grid grid-cols-2 md:grid-cols-4 gap-6 mt-8 pt-6 border-t border-slate-50 dark:border-slate-800/40">
                <div class="flex flex-col space-y-1">
                  <span class="text-[9px] font-black text-slate-300 dark:text-slate-600 uppercase tracking-widest">Instructor</span>
                  <div class="flex items-center space-x-2 text-slate-600 dark:text-slate-300">
                    <User size={14} class="text-indigo-400 dark:text-indigo-500" />
                    <span class="text-xs font-bold truncate">{course.instructor}</span>
                  </div>
                </div>
                <div class="flex flex-col space-y-1">
                  <span class="text-[9px] font-black text-slate-300 dark:text-slate-600 uppercase tracking-widest">Department</span>
                  <div class="flex items-center space-x-2 text-slate-600 dark:text-slate-300">
                    <BookOpen size={14} class="text-indigo-400 dark:text-indigo-500" />
                    <span class="text-xs font-bold truncate">{course.department}</span>
                  </div>
                </div>
                <div class="flex flex-col space-y-1">
                  <span class="text-[9px] font-black text-slate-300 dark:text-slate-600 uppercase tracking-widest">Term</span>
                  <div class="flex items-center space-x-2 text-slate-600 dark:text-slate-300">
                    <Calendar size={14} class="text-indigo-400 dark:text-indigo-500" />
                    <span class="text-xs font-bold">{course.term}</span>
                  </div>
                </div>
                <div class="flex flex-col space-y-1">
                  <span class="text-[9px] font-black text-slate-300 dark:text-slate-600 uppercase tracking-widest">Delivery</span>
                  <div class="flex items-center space-x-2 text-slate-600 dark:text-slate-300">
                    <MapPin size={14} class="text-indigo-400 dark:text-indigo-500" />
                    <span class="text-xs font-bold">{course.delivery_method || 'N/A'}</span>
                  </div>
                </div>
              </div>
            </div>
          {:else}
            <div class="bg-white p-24 rounded-2xl border border-slate-200 border-dashed flex flex-col items-center justify-center text-center dark:bg-slate-900 dark:border-slate-800 dark:border-dashed">
               <div class="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center text-slate-300 mb-4 dark:bg-slate-950 dark:text-slate-700">
                 <Search size={32} />
               </div>
               <h3 class="text-lg font-bold text-slate-800 dark:text-slate-200">No results matched your filters</h3>
               <p class="text-slate-500 dark:text-slate-400 text-sm mt-1">Try adjusting your keywords or clearing the active filters.</p>
               <button onclick={clearFilters} class="mt-6 px-6 py-2 bg-indigo-600 text-white rounded-xl text-sm font-bold shadow-lg shadow-indigo-200 dark:shadow-none">Clear all filters</button>
            </div>
          {/each}
        </div>

        <!-- Pagination UI -->
        {#if totalHits > limit}
          <div class="flex items-center justify-between pt-8 border-t border-slate-100 dark:border-slate-800">
            <div class="text-sm text-slate-500 dark:text-slate-400">
              Showing <span class="font-bold text-slate-700 dark:text-slate-300">{offset + 1}</span> to 
              <span class="font-bold text-slate-700 dark:text-slate-300">{Math.min(offset + limit, totalHits)}</span> of 
              <span class="font-bold text-slate-700 dark:text-slate-300">{totalHits.toLocaleString()}</span>
            </div>
            <div class="flex space-x-2">
              <button 
                onclick={() => handlePageChange(offset - limit)}
                disabled={offset === 0}
                class="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors dark:bg-slate-900 dark:border-slate-800 dark:text-slate-300 dark:hover:bg-slate-800/60"
              >
                Previous
              </button>
              <button 
                onclick={() => handlePageChange(offset + limit)}
                disabled={offset + limit >= totalHits}
                class="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors dark:bg-slate-900 dark:border-slate-800 dark:text-slate-300 dark:hover:bg-slate-800/60"
              >
                Next
              </button>
            </div>
          </div>
        {/if}
      {/if}
    </div>
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
  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: #cbd5e1;
  }
  :global(.dark) .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: #475569;
  }
</style>
