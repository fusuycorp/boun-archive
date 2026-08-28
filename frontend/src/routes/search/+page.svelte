<script lang="ts">
  import { onMount } from "svelte";
  import { Search, Filter, X, Download } from "lucide-svelte";
  import { API_BASE } from "$lib/config";
  import { exportToCSV } from "$lib/utils";
  import { goto } from "$app/navigation";
  import { page } from "$app/state";
  import SearchFacetDrawer from "$lib/components/search/SearchFacetDrawer.svelte";
  import SearchResultTable from "$lib/components/search/SearchResultTable.svelte";
  import SearchResultCard from "$lib/components/search/SearchResultCard.svelte";

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

  let searchAbortController: AbortController | null = null;

  async function fetchGlobalFacets() {
    try {
      const response = await fetch(`${API_BASE}/v1/facets`);
      if (response.ok) {
        globalFacets = await response.json();
      }
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
      if (response.ok) {
        const data = await response.json();
        results = data.hits || [];
        currentFacets = data.facetDistribution || {};
        totalHits = data.totalHits ?? data.estimatedTotalHits ?? 0;
      }
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
    
    const exportData = results.map(r => ({
      course_code: r.course_code,
      section: r.section,
      title: r.title,
      department: r.department,
      instructor: r.instructor,
      credits: r.credits,
      ects: r.ects,
      term: r.term,
      delivery_method: r.delivery_method
    }));
    
    exportToCSV(exportData, `boun_courses_search_${new Date().toISOString().split('T')[0]}`);
  }

  let debounceTimer: any;
  function handleInput() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => performSearch(true), 300);
  }

  onMount(() => {
    fetchGlobalFacets();
    
    // Parse URL search params on mount
    const urlParams = page.url.searchParams;
    query = urlParams.get("q") || "";
    offset = parseInt(urlParams.get("offset") || "0");
    limit = parseInt(urlParams.get("limit") || "20");
    sortColumn = urlParams.get("sort_by") || "";
    sortDirection = (urlParams.get("sort_order") as "asc" | "desc") || "asc";
    selectedTerms = urlParams.getAll("term");
    selectedDepts = urlParams.getAll("dept");

    performSearch(false);
  });
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

    <div class="lg:hidden fixed inset-y-0 right-0 z-50 w-80 max-w-[85vw] bg-white dark:bg-[#0f172a] border-l border-slate-200/80 dark:border-slate-800/80 shadow-2xl flex flex-col">
      <div class="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-950/50">
        <div class="flex items-center space-x-2 text-slate-700 dark:text-slate-200 font-bold">
          <Filter size={18} class="text-[#0080c9] dark:text-sky-400" />
          <span>Filters</span>
          {#if selectedTerms.length + selectedDepts.length > 0}
            <span class="px-2 py-0.5 bg-[#002d72] text-white rounded-full text-xs font-black">
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
        <SearchFacetDrawer 
          {globalFacets}
          {currentFacets}
          {selectedTerms}
          {selectedDepts}
          {deptSearch}
          onToggleTerm={toggleTerm}
          onToggleDept={toggleDept}
          onDeptSearchChange={(val) => deptSearch = val}
        />
      </div>

      <div class="p-4 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/50 flex space-x-2">
        <button 
          onclick={clearFilters}
          class="flex-1 py-2.5 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-bold rounded-xl hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors cursor-pointer"
        >
          Clear
        </button>
        <button 
          onclick={() => isFilterDrawerOpen = false}
          class="flex-1 py-2.5 bg-[#002d72] text-white text-xs font-bold rounded-xl hover:bg-[#001f52] transition-colors shadow-sm cursor-pointer"
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
         class="lg:hidden flex items-center space-x-1.5 bg-white dark:bg-[#0f172a] border border-slate-200/80 dark:border-slate-800/80 text-slate-700 dark:text-slate-300 px-3 py-1.5 rounded-full text-xs font-bold shadow-2xs hover:border-[#0080c9] transition-colors cursor-pointer"
       >
         <Filter size={14} class="text-[#0080c9] dark:text-sky-400" />
         <span>Filters</span>
         {#if selectedTerms.length + selectedDepts.length > 0}
           <span class="px-1.5 py-0.2 bg-[#002d72] text-white rounded-full text-[10px] font-black leading-none">
             {selectedTerms.length + selectedDepts.length}
           </span>
         {/if}
       </button>

       {#if selectedTerms.length > 0 || selectedDepts.length > 0 || query || sortColumn}
          <button 
            onclick={clearFilters}
            class="text-xs font-bold text-[#002d72] hover:text-[#001f52] dark:text-sky-300 dark:hover:text-sky-200 flex items-center space-x-1 bg-[#002d72]/10 dark:bg-sky-500/15 px-3 py-1.5 rounded-full transition-colors cursor-pointer"
          >
            <X size={14} />
            <span>Clear All</span>
          </button>
       {/if}

       <div class="flex items-center space-x-2 text-xs sm:text-sm text-slate-500 font-medium bg-white px-3 py-1.5 rounded-full border border-slate-200/80 dark:bg-[#0f172a] dark:border-slate-800/80 dark:text-slate-400 shadow-2xs">
         <span class="text-slate-800 dark:text-slate-100 font-bold">{totalHits.toLocaleString()}</span> 
         <span class="text-[11px] text-slate-400">results</span>
       </div>
       
       <div class="flex items-center space-x-1.5 bg-white px-2.5 py-1.5 rounded-full border border-slate-200/80 dark:bg-[#0f172a] dark:border-slate-800/80 shadow-2xs">
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
          class="flex items-center space-x-1.5 bg-[#002d72] text-white px-3 sm:px-4 py-1.5 rounded-full text-xs font-bold hover:bg-[#001f52] transition-colors shadow-xs disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
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
      <div class="bg-white rounded-2xl border border-slate-200/80 shadow-2xs overflow-hidden sticky top-24 dark:bg-[#0f172a] dark:border-slate-800/80">
        <div class="p-5 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between dark:border-slate-800 dark:bg-slate-950/50">
          <div class="flex items-center space-x-2 text-slate-700 dark:text-slate-300 font-bold">
            <Filter size={18} class="text-[#0080c9] dark:text-sky-400" />
            <span>Filters</span>
          </div>
        </div>

        <div class="p-5 space-y-8 max-h-[calc(100vh-200px)] overflow-y-auto custom-scrollbar">
          <SearchFacetDrawer 
            {globalFacets}
            {currentFacets}
            {selectedTerms}
            {selectedDepts}
            {deptSearch}
            onToggleTerm={toggleTerm}
            onToggleDept={toggleDept}
            onDeptSearchChange={(val) => deptSearch = val}
          />
        </div>
      </div>
    </aside>

    <!-- Search Results -->
    <div class="lg:col-span-3 space-y-6">
      <div class="relative group">
        <Search class="absolute left-4 sm:left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#0080c9] dark:group-focus-within:text-sky-400 transition-colors" size={20} />
        <input
          type="text"
          bind:value={query}
          oninput={handleInput}
          placeholder="Search 140,000+ historical courses..."
          class="w-full pl-11 sm:pl-14 pr-4 sm:pr-6 py-3.5 sm:py-4 bg-white border border-slate-200/80 rounded-2xl shadow-2xs outline-none focus:ring-4 focus:ring-[#0080c9]/10 focus:border-[#0080c9] text-base sm:text-lg transition-all dark:bg-[#0f172a] dark:border-slate-800/80 dark:text-white dark:focus:border-sky-400 dark:focus:ring-sky-500/20"
        />
      </div>

      {#if loading}
        <div class="flex flex-col items-center justify-center py-20 space-y-4">
          <div class="animate-spin rounded-full h-10 w-10 border-4 border-slate-100 border-t-[#002d72] dark:border-slate-800 dark:border-t-sky-400"></div>
          <p class="text-slate-500 dark:text-slate-400 font-medium text-sm animate-pulse">Searching archive...</p>
        </div>
      {:else}
        <!-- Mobile Cards List View (Visible on < sm) -->
        <div class="block sm:hidden space-y-3">
          {#each results as course}
            <SearchResultCard {course} />
          {:else}
            <div class="bg-white p-12 rounded-2xl border border-slate-200/80 text-center dark:bg-[#0f172a] dark:border-slate-800/80">
              <div class="w-12 h-12 bg-slate-50 rounded-full flex items-center justify-center text-slate-300 mx-auto mb-3 dark:bg-slate-950 dark:text-slate-700">
                <Search size={24} />
              </div>
              <h3 class="text-base font-bold text-slate-800 dark:text-slate-200">No results found</h3>
              <p class="text-slate-500 dark:text-slate-400 text-xs mt-1">Try adjusting your query or filters.</p>
            </div>
          {/each}
        </div>

        <!-- Desktop Table View (Visible on >= sm) -->
        <div class="hidden sm:block">
          {#if results.length > 0}
            <SearchResultTable 
              {results}
              {sortColumn}
              {sortDirection}
              onSort={handleSort}
            />
          {:else}
            <div class="bg-white p-24 rounded-2xl border border-slate-200/80 text-center dark:bg-[#0f172a] dark:border-slate-800/80">
              <div class="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center text-slate-300 mb-4 dark:bg-slate-950 dark:text-slate-700 mx-auto">
                <Search size={32} />
              </div>
              <h3 class="text-lg font-bold text-slate-800 dark:text-slate-200">No results found</h3>
              <p class="text-slate-500 dark:text-slate-400 text-sm mt-1">Try adjusting your filters or search terms.</p>
            </div>
          {/if}
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
                class="flex-1 sm:flex-none px-4 py-2 bg-white border border-slate-200/80 rounded-xl text-xs sm:text-sm font-bold text-slate-600 hover:bg-slate-50 hover:text-[#002d72] disabled:opacity-50 disabled:cursor-not-allowed transition-colors dark:bg-[#0f172a] dark:border-slate-800/80 dark:text-slate-300 dark:hover:bg-slate-800/60 shadow-2xs cursor-pointer"
              >
                Previous
              </button>
              <button 
                onclick={() => handlePageChange(offset + limit)}
                disabled={offset + limit >= totalHits}
                class="flex-1 sm:flex-none px-4 py-2 bg-white border border-slate-200/80 rounded-xl text-xs sm:text-sm font-bold text-slate-600 hover:bg-slate-50 hover:text-[#002d72] disabled:opacity-50 disabled:cursor-not-allowed transition-colors dark:bg-[#0f172a] dark:border-slate-800/80 dark:text-slate-300 dark:hover:bg-slate-800/60 shadow-2xs cursor-pointer"
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
