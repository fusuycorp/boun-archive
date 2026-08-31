<script lang="ts">
  import { onMount } from "svelte";
  import { Search, Filter, X, Download } from "lucide-svelte";
  import { API_BASE } from "$lib/config";
  import { exportToCSV } from "$lib/utils";
  import { goto } from "$app/navigation";
  import { page } from "$app/state";
  import type { SearchCourseHit, FacetDistribution } from "$lib/types";
  import SearchFacetDrawer from "$lib/components/search/SearchFacetDrawer.svelte";
  import SearchResultTable from "$lib/components/search/SearchResultTable.svelte";
  import SearchResultCard from "$lib/components/search/SearchResultCard.svelte";

  let query = $state("");
  let results = $state<SearchCourseHit[]>([]);
  let currentFacets = $state<FacetDistribution>({});
  let globalFacets = $state<FacetDistribution>({});
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
        const isUnfiltered = selectedTerms.length === 0 && selectedDepts.length === 0 && !query.trim();
        if (isUnfiltered && (!globalFacets?.term || Object.keys(globalFacets.term).length === 0) && data.facetDistribution) {
          globalFacets = data.facetDistribution;
        }
      }
    } catch (e) {
      if (e instanceof Error && e.name === 'AbortError') return;
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
    performSearch(true);
  }

  function toggleDept(dept: string) {
    if (selectedDepts.includes(dept)) {
      selectedDepts = selectedDepts.filter(d => d !== dept);
    } else {
      selectedDepts = [...selectedDepts, dept];
    }
    performSearch(true);
  }

  function clearFilters() {
    selectedTerms = [];
    selectedDepts = [];
    query = "";
    sortColumn = "";
    sortDirection = "asc";
    performSearch(true);
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

  let debounceTimer: ReturnType<typeof setTimeout> | undefined;
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
      class="lg:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-xs transition-opacity cursor-pointer"
    ></div>

    <div class="lg:hidden fixed inset-y-0 right-0 z-50 w-80 max-w-[85vw] bg-white dark:bg-[#121827] border-l border-[#e5e0d8] dark:border-[#1e293b] shadow-2xl flex flex-col">
      <div class="p-4 border-b border-[#e5e0d8] dark:border-[#1e293b] flex items-center justify-between bg-[#f3efe6]/60 dark:bg-[#0a0e1a]">
        <div class="flex items-center space-x-2 text-[#161e2e] dark:text-slate-200 font-semibold text-sm">
          <Filter size={16} class="text-[#0080c9] dark:text-[#8cc8ea]" />
          <span>Filters</span>
          {#if selectedTerms.length + selectedDepts.length > 0}
            <span class="px-2 py-0.5 bg-[#002d72] text-white dark:bg-[#8cc8ea] dark:text-[#0a0e1a] rounded-full font-mono text-xs font-bold">
              {selectedTerms.length + selectedDepts.length}
            </span>
          {/if}
        </div>
        <button 
          onclick={() => isFilterDrawerOpen = false}
          class="p-1.5 text-[#525f7f] hover:text-[#002d72] dark:hover:text-slate-200 rounded-lg cursor-pointer"
          aria-label="Close filters"
        >
          <X size={19} />
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

      <div class="p-4 border-t border-[#e5e0d8] dark:border-[#1e293b] bg-[#f3efe6]/60 dark:bg-[#0a0e1a] flex space-x-2">
        <button 
          onclick={clearFilters}
          class="flex-1 py-2.5 bg-[#e5e0d8] dark:bg-slate-800 text-[#161e2e] dark:text-slate-300 text-xs font-semibold rounded-lg hover:bg-[#d8d2c7] dark:hover:bg-slate-700 transition-colors cursor-pointer"
        >
          Clear
        </button>
        <button 
          onclick={() => isFilterDrawerOpen = false}
          class="flex-1 py-2.5 bg-[#002d72] text-white text-xs font-semibold rounded-lg hover:bg-[#001b44] transition-colors shadow-2xs cursor-pointer"
        >
          Apply Filters
        </button>
      </div>
    </div>
  {/if}

  <!-- Header & Actions -->
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
    <div>
      <h1 class="font-serif text-2xl sm:text-3xl font-bold text-[#002d72] dark:text-slate-50 tracking-tight">Course Search</h1>
      <p class="font-sans text-xs sm:text-sm text-[#525f7f] mt-1 dark:text-slate-400">Search over 140,000 course records with multi-dimensional facets.</p>
    </div>

    <div class="flex flex-wrap items-center gap-2 sm:gap-3">
       <!-- Mobile Filter Toggle Button -->
       <button 
         onclick={() => isFilterDrawerOpen = true}
         class="lg:hidden flex items-center space-x-1.5 bg-white dark:bg-[#121827] border border-[#e5e0d8] dark:border-[#1e293b] text-[#161e2e] dark:text-slate-300 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-2xs hover:border-[#c5a059] transition-colors cursor-pointer"
       >
         <Filter size={14} class="text-[#0080c9] dark:text-[#8cc8ea]" />
         <span>Filters</span>
         {#if selectedTerms.length + selectedDepts.length > 0}
           <span class="px-1.5 py-0.2 bg-[#002d72] text-white dark:bg-[#8cc8ea] dark:text-[#0a0e1a] rounded-full font-mono text-[10px] font-bold leading-none">
             {selectedTerms.length + selectedDepts.length}
           </span>
         {/if}
       </button>

       {#if selectedTerms.length > 0 || selectedDepts.length > 0 || query || sortColumn}
          <button 
            onclick={clearFilters}
            class="text-xs font-semibold text-[#525f7f] dark:text-slate-300 hover:text-[#002d72] dark:hover:text-white flex items-center space-x-1 bg-[#e5e0d8] dark:bg-slate-800 px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
          >
            <X size={13} />
            <span>Clear</span>
          </button>
       {/if}

       <div class="flex items-center space-x-1.5 text-xs font-medium bg-white px-3 py-1.5 rounded-lg border border-[#e5e0d8] dark:bg-[#121827] dark:border-[#1e293b] text-[#525f7f] dark:text-slate-400 shadow-2xs">
         <span class="font-mono font-bold text-[#002d72] dark:text-slate-100">{totalHits.toLocaleString()}</span> 
         <span class="text-[11px] text-[#525f7f] dark:text-slate-400">results</span>
       </div>
       
       <div class="flex items-center space-x-1.5 bg-white px-2.5 py-1.5 rounded-lg border border-[#e5e0d8] dark:bg-[#121827] dark:border-[#1e293b] shadow-2xs">
         <span class="text-[9px] font-mono font-bold text-[#525f7f] dark:text-slate-400 uppercase tracking-wider">Show</span>
         <select 
          value={limit} 
          onchange={(e) => handleLimitChange(Number(e.currentTarget.value))}
          class="bg-transparent text-xs font-semibold text-[#161e2e] dark:text-slate-300 outline-none border-none focus:ring-0 cursor-pointer font-mono"
         >
           {#each limitOptions as option}
             <option value={option}>{option}</option>
           {/each}
         </select>
       </div>

       <button 
          onclick={handleExport}
          disabled={results.length === 0}
          class="flex items-center space-x-1.5 bg-[#002d72] text-white px-3 sm:px-4 py-1.5 rounded-lg text-xs font-semibold hover:bg-[#001b44] transition-colors shadow-2xs disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
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
      <div class="bg-white rounded-xl border border-[#e5e0d8] shadow-2xs overflow-hidden sticky top-24 dark:bg-[#121827] dark:border-[#1e293b]">
        <div class="p-4 border-b border-[#e5e0d8] bg-[#f3efe6]/60 flex items-center justify-between dark:border-[#1e293b] dark:bg-[#0a0e1a]">
          <div class="flex items-center space-x-2 text-[#002d72] dark:text-slate-200 font-semibold text-sm">
            <Filter size={16} class="text-[#0080c9] dark:text-[#8cc8ea]" />
            <span>Refine Search</span>
          </div>
        </div>

        <div class="p-5 space-y-7 max-h-[calc(100vh-200px)] overflow-y-auto custom-scrollbar">
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
    <div class="lg:col-span-3 space-y-5">
      <div class="relative group">
        <Search class="absolute left-4 top-1/2 -translate-y-1/2 text-[#525f7f] group-focus-within:text-[#002d72] dark:group-focus-within:text-[#8cc8ea] transition-colors" size={18} />
        <input
          type="text"
          bind:value={query}
          oninput={handleInput}
          placeholder="Search courses by code, title, or keyword..."
          class="w-full pl-11 pr-4 py-3.5 bg-white border border-[#e5e0d8] rounded-xl shadow-2xs outline-none focus:ring-2 focus:ring-[#002d72]/20 focus:border-[#002d72] text-sm sm:text-base transition-all dark:bg-[#121827] dark:border-[#1e293b] dark:text-white dark:focus:border-[#8cc8ea] dark:focus:ring-[#8cc8ea]/20"
        />
      </div>

      {#if loading}
        <div class="flex flex-col items-center justify-center py-20 space-y-3">
          <div class="animate-spin rounded-full h-8 w-8 border-3 border-[#e5e0d8] border-t-[#002d72] dark:border-slate-800 dark:border-t-[#8cc8ea]"></div>
          <p class="text-[#525f7f] dark:text-slate-400 font-medium text-xs">Querying archive corpus...</p>
        </div>
      {:else}
        <!-- Mobile Cards List View (Visible on < sm) -->
        <div class="block sm:hidden space-y-3">
          {#each results as course}
            <SearchResultCard {course} />
          {:else}
            <div class="bg-white p-12 rounded-xl border border-[#e5e0d8] text-center dark:bg-[#121827] dark:border-[#1e293b]">
              <div class="w-10 h-10 bg-[#f3efe6] rounded-full flex items-center justify-center text-[#525f7f] mx-auto mb-3 dark:bg-slate-800 dark:text-slate-400">
                <Search size={20} />
              </div>
              <h3 class="font-serif text-base font-bold text-[#161e2e] dark:text-slate-200">No matching records found</h3>
              <p class="text-[#525f7f] dark:text-slate-400 text-xs mt-1">Try adjusting query keywords or broadening active filters.</p>
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
            <div class="bg-white p-20 rounded-xl border border-[#e5e0d8] text-center dark:bg-[#121827] dark:border-[#1e293b]">
              <div class="w-12 h-12 bg-[#f3efe6] rounded-full flex items-center justify-center text-[#525f7f] mb-3 dark:bg-slate-800 dark:text-slate-400 mx-auto">
                <Search size={24} />
              </div>
              <h3 class="font-serif text-lg font-bold text-[#161e2e] dark:text-slate-200">No courses match your query</h3>
              <p class="text-[#525f7f] dark:text-slate-400 text-xs mt-1">Refine your search keywords or toggle term/department filters.</p>
            </div>
          {/if}
        </div>

        <!-- Pagination UI -->
        {#if totalHits > limit}
          <div class="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 sm:pt-6">
            <div class="text-xs text-[#525f7f] dark:text-slate-400 text-center sm:text-left font-mono">
              Showing <span class="font-bold text-[#161e2e] dark:text-slate-200">{offset + 1}</span> to 
              <span class="font-bold text-[#161e2e] dark:text-slate-200">{Math.min(offset + limit, totalHits)}</span> of 
              <span class="font-bold text-[#161e2e] dark:text-slate-200">{totalHits.toLocaleString()}</span>
            </div>
            <div class="flex space-x-2 w-full sm:w-auto justify-center">
              <button 
                onclick={() => handlePageChange(offset - limit)}
                disabled={offset === 0}
                class="flex-1 sm:flex-none px-4 py-2 bg-white border border-[#e5e0d8] rounded-lg text-xs font-semibold text-[#161e2e] hover:bg-[#f3efe6] hover:text-[#002d72] disabled:opacity-40 disabled:cursor-not-allowed transition-colors dark:bg-[#121827] dark:border-[#1e293b] dark:text-slate-300 dark:hover:bg-slate-800 shadow-2xs cursor-pointer"
              >
                Previous
              </button>
              <button 
                onclick={() => handlePageChange(offset + limit)}
                disabled={offset + limit >= totalHits}
                class="flex-1 sm:flex-none px-4 py-2 bg-white border border-[#e5e0d8] rounded-lg text-xs font-semibold text-[#161e2e] hover:bg-[#f3efe6] hover:text-[#002d72] disabled:opacity-40 disabled:cursor-not-allowed transition-colors dark:bg-[#121827] dark:border-[#1e293b] dark:text-slate-300 dark:hover:bg-slate-800 shadow-2xs cursor-pointer"
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
