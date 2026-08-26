<script lang="ts">
  import { onMount } from "svelte";
  import { Search, Filter, BookOpen, User, Calendar, MapPin, Check, X, ArrowUp, ArrowDown, ArrowUpDown, Download } from "lucide-svelte";
  import { API_BASE } from "$lib/config";
  import { exportToCSV } from "$lib/utils";
  import { goto } from "$app/navigation";
  import { page } from "$app/state";

  let query = $state("");
  let results = $state<any[]>([]);
  let currentFacets = $state<any>({});
  let globalFacets = $state<any>({});
  let loading = $state(false);
  let totalHits = $state(0);
  let offset = $state(0);
  let limit = $state(20);
  const limitOptions = [10, 20, 50, 100, 200];

  // Sorting
  let sortColumn = $state("");
  let sortDirection = $state<"asc" | "desc">("asc");

  // Filters
  let selectedTerms = $state<string[]>([]);
  let selectedDepts = $state<string[]>([]);
  let deptSearch = $state("");
  let isFilterDrawerOpen = $state(false);

  async function fetchGlobalFacets() {
    try {
      const response = await fetch(`${API_BASE}/v1/facets`);
      globalFacets = await response.json();
    } catch (e) {
      console.error("Failed to fetch facets", e);
    }
  }

  function updateURL() {
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (offset > 0) params.set("offset", offset.toString());
    if (limit !== 20) params.set("limit", limit.toString());
    if (sortColumn) {
      params.set("sort_by", sortColumn);
      params.set("sort_order", sortDirection);
    }
    selectedTerms.forEach(t => params.append("term", t));
    selectedDepts.forEach(d => params.append("dept", d));
    
    const newUrl = `${window.location.pathname}?${params.toString()}`;
    goto(newUrl, { replaceState: true, keepFocus: true, noScroll: true });
  }

  let searchAbortController: AbortController | null = null;

  async function performSearch(resetOffset = true) {
    if (searchAbortController) {
      searchAbortController.abort();
    }
    searchAbortController = new AbortController();

    loading = true;
    if (resetOffset) offset = 0;
    
    updateURL();

    try {
      const params = new URLSearchParams();
      params.append("q", query);
      params.append("limit", limit.toString());
      params.append("offset", offset.toString());
      
      if (sortColumn) {
        params.append("sort_by", sortColumn);
        params.append("sort_order", sortDirection);
      }
      
      selectedTerms.forEach(t => params.append("term", t));
      selectedDepts.forEach(d => params.append("dept", d));

      const response = await fetch(`${API_BASE}/v1/search?${params.toString()}`, {
        signal: searchAbortController.signal
      });
      const data = await response.json();
      results = data.hits;
      currentFacets = data.facetDistribution;
      // Meilisearch returns totalHits or estimatedTotalHits depending on configuration
      totalHits = data.totalHits ?? data.estimatedTotalHits ?? 0;
    } catch (e: any) {
      if (e.name === 'AbortError') return;
      console.error("Search failed", e);
    } finally {
      if (!searchAbortController.signal.aborted) {
        loading = false;
      }
    }
  }

  function handlePageChange(newOffset: number) {
    offset = newOffset;
    performSearch(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function handleLimitChange(newLimit: number) {
    limit = newLimit;
    performSearch(true);
  }

  function handleSort(column: string) {
    if (sortColumn === column) {
      sortDirection = sortDirection === "asc" ? "desc" : "asc";
    } else {
      sortColumn = column;
      sortDirection = "asc";
    }
    performSearch(true);
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
    sortColumn = "";
    sortDirection = "asc";
    performSearch();
  }

  function handleExport() {
    if (results.length === 0) return;
    
    // Clean data for export
    const exportData = results.map(c => ({
      course_code: c.course_code,
      section: c.section,
      title: c.title,
      department: c.department,
      instructor: c.instructor,
      credits: c.credits,
      ects: c.ects,
      term: c.term,
      delivery_method: c.delivery_method
    }));
    
    exportToCSV(exportData, `boun_courses_export_${new Date().toISOString().split('T')[0]}`);
  }

  // Debounced search
  let timeout: any;
  function handleInput() {
    clearTimeout(timeout);
    timeout = setTimeout(performSearch, 300);
  }

  onMount(async () => {
    await fetchGlobalFacets();
    
    // Restore state from URL search params
    const params = page.url.searchParams;
    if (params.toString()) {
      query = params.get("q") || "";
      offset = parseInt(params.get("offset") || "0");
      limit = parseInt(params.get("limit") || "20");
      sortColumn = params.get("sort_by") || "";
      sortDirection = (params.get("sort_order") as any) || "asc";
      selectedTerms = params.getAll("term") || [];
      selectedDepts = params.getAll("dept") || [];
      performSearch(false); // Search without resetting offset
    } else {
      performSearch();
    }
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
  <!-- Mobile Filter Modal / Drawer -->
  {#if isFilterDrawerOpen}
    <div 
      role="button"
      tabindex="0"
      aria-label="Close filter drawer"
      onclick={() => isFilterDrawerOpen = false}
      onkeydown={(e) => (e.key === 'Escape' || e.key === 'Enter') && (isFilterDrawerOpen = false)}
      class="lg:hidden fixed inset-0 z-40 bg-slate-950/60 backdrop-blur-xs transition-opacity cursor-pointer"
    ></div>

    <div class="lg:hidden fixed inset-y-0 right-0 z-50 w-80 max-w-[85vw] bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col">
      <div class="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-950/50">
        <div class="flex items-center space-x-2 text-slate-700 dark:text-slate-200 font-bold">
          <Filter size={18} />
          <span>Filters</span>
          {#if selectedTerms.length + selectedDepts.length > 0}
            <span class="px-2 py-0.5 bg-indigo-600 text-white rounded-full text-xs font-black">
              {selectedTerms.length + selectedDepts.length}
            </span>
          {/if}
        </div>
        <button 
          onclick={() => isFilterDrawerOpen = false}
          class="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg cursor-pointer"
          aria-label="Close filters"
        >
          <X size={20} />
        </button>
      </div>

      <div class="p-4 space-y-6 flex-1 overflow-y-auto custom-scrollbar">
        <!-- Term Filter -->
        <div class="space-y-3">
          <div class="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center justify-between">
            <span>Academic Term</span>
            <span class="text-indigo-500 dark:text-indigo-400 font-mono">{selectedTerms.length || ''}</span>
          </div>
          <div class="space-y-1 max-h-48 overflow-y-auto pr-1 custom-scrollbar">
            {#if globalFacets.term}
              {#each Object.keys(globalFacets.term).sort().reverse() as term}
                <button 
                  onclick={() => toggleTerm(term)}
                  class="w-full flex items-center justify-between p-2 rounded-lg text-xs transition-all cursor-pointer
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
          <div class="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center justify-between">
            <span>Department</span>
            <span class="text-indigo-500 dark:text-indigo-400 font-mono">{selectedDepts.length || ''}</span>
          </div>
          
          <div class="relative">
            <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" size={12} />
            <input 
              type="text" 
              bind:value={deptSearch}
              placeholder="Filter departments..."
              class="w-full pl-8 pr-2 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-xs outline-none focus:ring-1 focus:ring-indigo-500 dark:bg-slate-950 dark:border-slate-800 dark:text-slate-200"
            />
          </div>

          <div class="space-y-1 max-h-60 overflow-y-auto pr-1 custom-scrollbar">
            {#each filteredDepts as dept}
              <button 
                onclick={() => toggleDept(dept)}
                class="w-full flex items-center justify-between p-2 rounded-lg text-xs transition-all cursor-pointer
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

      <div class="p-4 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/50 flex space-x-2">
        <button 
          onclick={clearFilters}
          class="flex-1 py-2.5 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-bold rounded-xl hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
        >
          Clear
        </button>
        <button 
          onclick={() => isFilterDrawerOpen = false}
          class="flex-1 py-2.5 bg-indigo-600 text-white text-xs font-bold rounded-xl hover:bg-indigo-700 transition-colors shadow-sm"
        >
          Apply Filters
        </button>
      </div>
    </div>
  {/if}

  <!-- Header & Actions -->
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
    <div>
      <h2 class="text-2xl sm:text-3xl font-black text-slate-800 dark:text-slate-100 tracking-tight">Course Search</h2>
      <p class="text-xs sm:text-sm text-slate-500 mt-1 dark:text-slate-400">Search over 140,000 course records with instant facets.</p>
    </div>

    <div class="flex flex-wrap items-center gap-2 sm:gap-3">
       <!-- Mobile Filter Toggle Button -->
       <button 
         onclick={() => isFilterDrawerOpen = true}
         class="lg:hidden flex items-center space-x-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 px-3 py-1.5 rounded-full text-xs font-bold shadow-xs hover:border-indigo-500 transition-colors cursor-pointer"
       >
         <Filter size={14} class="text-indigo-600 dark:text-indigo-400" />
         <span>Filters</span>
         {#if selectedTerms.length + selectedDepts.length > 0}
           <span class="px-1.5 py-0.2 bg-indigo-600 text-white rounded-full text-[10px] font-black leading-none">
             {selectedTerms.length + selectedDepts.length}
           </span>
         {/if}
       </button>

       {#if selectedTerms.length > 0 || selectedDepts.length > 0 || query || sortColumn}
          <button 
            onclick={clearFilters}
            class="text-xs font-bold text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-300 flex items-center space-x-1 bg-indigo-50 dark:bg-indigo-950/40 px-3 py-1.5 rounded-full transition-colors cursor-pointer"
          >
            <X size={14} />
            <span>Clear All</span>
          </button>
       {/if}

       <div class="flex items-center space-x-2 text-xs sm:text-sm text-slate-500 font-medium bg-white px-3 py-1.5 rounded-full border border-slate-200 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-400 shadow-xs">
         <span class="text-slate-800 dark:text-slate-100 font-bold">{totalHits.toLocaleString()}</span> 
         <span class="text-[11px] text-slate-400">results</span>
       </div>
       
       <div class="flex items-center space-x-1.5 bg-white px-2.5 py-1.5 rounded-full border border-slate-200 dark:bg-slate-900 dark:border-slate-800 shadow-xs">
         <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest">Show</span>
         <select 
          value={limit} 
          onchange={(e) => handleLimitChange(Number(e.currentTarget.value))}
          class="bg-transparent text-xs font-bold text-slate-700 dark:text-slate-300 outline-none border-none focus:ring-0 cursor-pointer"
         >
           {#each limitOptions as option}
             <option value={option}>{option}</option>
           {/each}
         </select>
       </div>

       <button 
          onclick={handleExport}
          disabled={results.length === 0}
          class="flex items-center space-x-1.5 bg-indigo-600 text-white px-3 sm:px-4 py-1.5 rounded-full text-xs font-bold hover:bg-indigo-700 transition-colors shadow-sm dark:shadow-none disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
       >
         <Download size={13} />
         <span class="hidden xs:inline">Export</span>
         <span class="xs:hidden">CSV</span>
       </button>
    </div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-4 gap-6 lg:gap-8">
    <!-- Desktop Sidebar Filters -->
    <aside class="hidden lg:block space-y-6">
      <div class="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden sticky top-24 dark:bg-slate-900 dark:border-slate-800">
        <div class="p-5 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between dark:border-slate-800 dark:bg-slate-950/50">
          <div class="flex items-center space-x-2 text-slate-700 dark:text-slate-300 font-bold">
            <Filter size={18} />
            <span>Filters</span>
          </div>
        </div>

        <div class="p-5 space-y-8 max-h-[calc(100vh-200px)] overflow-y-auto custom-scrollbar">
          <!-- Term Filter -->
          <div class="space-y-3">
            <div class="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center justify-between">
              <span>Academic Term</span>
              <span class="text-indigo-500 dark:text-indigo-400 font-mono">{selectedTerms.length || ''}</span>
            </div>
            <div class="space-y-1 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
              {#if globalFacets.term}
                {#each Object.keys(globalFacets.term).sort().reverse() as term}
                  <button 
                    onclick={() => toggleTerm(term)}
                    class="w-full flex items-center justify-between p-2 rounded-lg text-sm transition-all cursor-pointer
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
            <div class="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest flex items-center justify-between">
              <span>Department</span>
              <span class="text-indigo-500 dark:text-indigo-400 font-mono">{selectedDepts.length || ''}</span>
            </div>
            
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
                  class="w-full flex items-center justify-between p-2 rounded-lg text-sm transition-all cursor-pointer
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
        <Search class="absolute left-4 sm:left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-indigo-500 dark:group-focus-within:text-indigo-400 transition-colors" size={20} />
        <input
          type="text"
          bind:value={query}
          oninput={handleInput}
          placeholder="Search 140,000+ historical courses..."
          class="w-full pl-11 sm:pl-14 pr-4 sm:pr-6 py-3.5 sm:py-5 bg-white border border-slate-200 rounded-2xl shadow-xs outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 text-base sm:text-xl transition-all dark:bg-slate-900 dark:border-slate-800 dark:text-white dark:focus:border-indigo-500 dark:focus:ring-indigo-500/20"
        />
      </div>

      {#if loading}
        <div class="flex flex-col items-center justify-center py-20 space-y-4">
          <div class="animate-spin rounded-full h-10 w-10 border-4 border-slate-100 border-t-indigo-600 dark:border-slate-800 dark:border-t-indigo-500"></div>
          <p class="text-slate-500 dark:text-slate-400 font-medium text-sm animate-pulse">Searching archive...</p>
        </div>
      {:else}
        <!-- Mobile Cards List View (Visible on < sm) -->
        <div class="block sm:hidden space-y-3">
          {#each results as course}
            <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs dark:bg-slate-900 dark:border-slate-800 space-y-2.5">
              <div class="flex items-start justify-between gap-2">
                <div>
                  <div class="flex items-center space-x-2">
                    <span class="text-sm font-black text-indigo-600 dark:text-indigo-400">{course.course_code}</span>
                    <span class="text-[10px] font-bold px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 rounded">Sec {course.section}</span>
                  </div>
                  <a 
                    href="/course/{course.course_code}"
                    class="text-sm font-bold text-slate-800 dark:text-slate-100 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors block mt-1"
                  >
                    {course.title}
                  </a>
                </div>
                <span class="text-[10px] font-bold px-2 py-0.5 bg-indigo-50 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300 rounded-full shrink-0 font-mono">
                  {course.term}
                </span>
              </div>

              <div class="text-xs text-slate-400 dark:text-slate-500 truncate">
                {course.department}
              </div>

              <div class="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800/80 text-xs">
                <div class="flex items-center space-x-1.5 text-slate-600 dark:text-slate-300 font-medium truncate max-w-[180px]">
                  <User size={13} class="text-slate-400 shrink-0" />
                  <span class="truncate">{course.instructor}</span>
                </div>
                <div class="flex items-center space-x-1.5 text-slate-500 dark:text-slate-400 font-mono text-[11px] shrink-0">
                  <span class="font-bold text-slate-700 dark:text-slate-300">{course.credits} Cr</span>
                  <span>•</span>
                  <span>{course.ects} ECTS</span>
                </div>
              </div>
            </div>
          {:else}
            <div class="bg-white p-12 rounded-2xl border border-slate-200 text-center dark:bg-slate-900 dark:border-slate-800">
              <div class="w-12 h-12 bg-slate-50 rounded-full flex items-center justify-center text-slate-300 mx-auto mb-3 dark:bg-slate-950 dark:text-slate-700">
                <Search size={24} />
              </div>
              <h3 class="text-base font-bold text-slate-800 dark:text-slate-200">No results found</h3>
              <p class="text-slate-500 dark:text-slate-400 text-xs mt-1">Try adjusting your query or filters.</p>
            </div>
          {/each}
        </div>

        <!-- Desktop Table View (Visible on >= sm) -->
        <div class="hidden sm:block bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden dark:bg-slate-900 dark:border-slate-800">
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/50 dark:bg-slate-950/50 border-b border-slate-100 dark:border-slate-800">
                  <th class="p-4">
                    <button 
                      onclick={() => handleSort('course_code')}
                      class="flex items-center space-x-1 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest hover:text-indigo-600 transition-colors cursor-pointer"
                    >
                      <span>Course</span>
                      {#if sortColumn === 'course_code'}
                        {sortDirection === 'asc' ? '↑' : '↓'}
                      {:else}
                        <ArrowUpDown size={10} />
                      {/if}
                    </button>
                  </th>
                  <th class="p-4">
                    <button 
                      onclick={() => handleSort('title')}
                      class="flex items-center space-x-1 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest hover:text-indigo-600 transition-colors cursor-pointer"
                    >
                      <span>Title</span>
                      {#if sortColumn === 'title'}
                        {sortDirection === 'asc' ? '↑' : '↓'}
                      {:else}
                        <ArrowUpDown size={10} />
                      {/if}
                    </button>
                  </th>
                  <th class="p-4">
                    <button 
                      onclick={() => handleSort('instructor')}
                      class="flex items-center space-x-1 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest hover:text-indigo-600 transition-colors cursor-pointer"
                    >
                      <span>Instructor</span>
                      {#if sortColumn === 'instructor'}
                        {sortDirection === 'asc' ? '↑' : '↓'}
                      {:else}
                        <ArrowUpDown size={10} />
                      {/if}
                    </button>
                  </th>
                  <th class="p-4 text-center">
                    <button 
                      onclick={() => handleSort('credits')}
                      class="flex items-center justify-center space-x-1 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest hover:text-indigo-600 transition-colors mx-auto cursor-pointer"
                    >
                      <span>Cr</span>
                      {#if sortColumn === 'credits'}
                        {sortDirection === 'asc' ? '↑' : '↓'}
                      {:else}
                        <ArrowUpDown size={10} />
                      {/if}
                    </button>
                  </th>
                  <th class="p-4">
                    <button 
                      onclick={() => handleSort('term')}
                      class="flex items-center space-x-1 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest hover:text-indigo-600 transition-colors cursor-pointer"
                    >
                      <span>Term</span>
                      {#if sortColumn === 'term'}
                        {sortDirection === 'asc' ? '↑' : '↓'}
                      {:else}
                        <ArrowUpDown size={10} />
                      {/if}
                    </button>
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-50 dark:divide-slate-800/50">
                {#each results as course}
                  <tr class="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors group">
                    <td class="p-4 whitespace-nowrap">
                      <div class="flex flex-col">
                        <span class="text-sm font-bold text-indigo-600 dark:text-indigo-400">{course.course_code}</span>
                        <span class="text-[10px] text-slate-400 font-medium">Sec {course.section}</span>
                      </div>
                    </td>
                    <td class="p-4">
                      <div class="flex flex-col">
                        <a 
                          href="/course/{course.course_code}"
                          class="text-sm font-bold text-slate-800 dark:text-slate-100 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors"
                        >
                          {course.title}
                        </a>
                        <span class="text-[10px] text-slate-400 dark:text-slate-500 truncate max-w-[220px]">{course.department}</span>
                      </div>
                    </td>
                    <td class="p-4 whitespace-nowrap">
                      <div class="flex items-center space-x-2">
                        <User size={14} class="text-slate-300 dark:text-slate-600" />
                        <span class="text-xs font-medium text-slate-600 dark:text-slate-300">{course.instructor}</span>
                      </div>
                    </td>
                    <td class="p-4 whitespace-nowrap text-center">
                      <div class="flex flex-col items-center">
                        <span class="text-xs font-bold text-slate-700 dark:text-slate-300">{course.credits}</span>
                        <span class="text-[9px] text-slate-400 uppercase font-bold">{course.ects} ECTS</span>
                      </div>
                    </td>
                    <td class="p-4 whitespace-nowrap">
                      <div class="flex items-center space-x-2">
                        <Calendar size={14} class="text-slate-300 dark:text-slate-600" />
                        <span class="text-xs font-medium text-slate-600 dark:text-slate-300">{course.term}</span>
                      </div>
                    </td>
                  </tr>
                {:else}
                  <tr>
                    <td colspan="5" class="p-24 text-center">
                      <div class="flex flex-col items-center justify-center">
                        <div class="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center text-slate-300 mb-4 dark:bg-slate-950 dark:text-slate-700">
                          <Search size={32} />
                        </div>
                        <h3 class="text-lg font-bold text-slate-800 dark:text-slate-200">No results found</h3>
                        <p class="text-slate-500 dark:text-slate-400 text-sm mt-1">Try adjusting your filters or search terms.</p>
                      </div>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Pagination UI -->
        {#if totalHits > limit}
          <div class="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 sm:pt-8">
            <div class="text-xs sm:text-sm text-slate-500 dark:text-slate-400 text-center sm:text-left">
              Showing <span class="font-bold text-slate-700 dark:text-slate-300">{offset + 1}</span> to 
              <span class="font-bold text-slate-700 dark:text-slate-300">{Math.min(offset + limit, totalHits)}</span> of 
              <span class="font-bold text-slate-700 dark:text-slate-300">{totalHits.toLocaleString()}</span>
            </div>
            <div class="flex space-x-2 w-full sm:w-auto justify-center">
              <button 
                onclick={() => handlePageChange(offset - limit)}
                disabled={offset === 0}
                class="flex-1 sm:flex-none px-4 py-2 bg-white border border-slate-200 rounded-xl text-xs sm:text-sm font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors dark:bg-slate-900 dark:border-slate-800 dark:text-slate-300 dark:hover:bg-slate-800/60 shadow-xs cursor-pointer"
              >
                Previous
              </button>
              <button 
                onclick={() => handlePageChange(offset + limit)}
                disabled={offset + limit >= totalHits}
                class="flex-1 sm:flex-none px-4 py-2 bg-white border border-slate-200 rounded-xl text-xs sm:text-sm font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors dark:bg-slate-900 dark:border-slate-800 dark:text-slate-300 dark:hover:bg-slate-800/60 shadow-xs cursor-pointer"
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

