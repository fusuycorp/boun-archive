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
  <div class="flex items-center justify-between">
    <h2 class="text-3xl font-bold text-slate-800 dark:text-slate-100">Course Search</h2>
    <div class="flex items-center space-x-4">
       {#if selectedTerms.length > 0 || selectedDepts.length > 0 || query || sortColumn}
          <button 
            onclick={clearFilters}
            class="text-xs font-bold text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-300 flex items-center space-x-1 bg-indigo-50 dark:bg-indigo-950/40 px-3 py-1.5 rounded-full transition-colors"
          >
            <X size={14} />
            <span>Clear All</span>
          </button>
       {/if}
       <div class="flex items-center space-x-2 text-sm text-slate-500 font-medium bg-white px-3 py-1.5 rounded-full border border-slate-200 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-400 shadow-sm">
         <span class="text-slate-800 dark:text-slate-100 font-bold">{totalHits.toLocaleString()}</span> 
         <span class="text-xs text-slate-400">results found</span>
       </div>
       
       <div class="flex items-center space-x-2 bg-white px-3 py-1.5 rounded-full border border-slate-200 dark:bg-slate-900 dark:border-slate-800 shadow-sm">
         <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Show</span>
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
          class="flex items-center space-x-2 bg-indigo-600 text-white px-4 py-1.5 rounded-full text-xs font-bold hover:bg-indigo-700 transition-colors shadow-lg shadow-indigo-200 dark:shadow-none disabled:opacity-50 disabled:cursor-not-allowed"
       >
         <Download size={14} />
         <span>Export CSV</span>
       </button>
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
        <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden dark:bg-slate-900 dark:border-slate-800">
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/50 dark:bg-slate-950/50 border-b border-slate-100 dark:border-slate-800">
                  <th class="p-4">
                    <button 
                      onclick={() => handleSort('course_code')}
                      class="flex items-center space-x-1 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest hover:text-indigo-600 transition-colors"
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
                      class="flex items-center space-x-1 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest hover:text-indigo-600 transition-colors"
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
                      class="flex items-center space-x-1 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest hover:text-indigo-600 transition-colors"
                    >
                      <span>Instructor</span>
                      {#if sortColumn === 'instructor'}
                        {sortDirection === 'asc' ? '↑' : '↓'}
                      {:else}
                        <ArrowUpDown size={10} />
                      {/if}
                    </button>
                  </th>
                  <th class="p-4">
                    <div class="flex flex-col items-center">
                      <button 
                        onclick={() => handleSort('credits')}
                        class="flex items-center space-x-1 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest hover:text-indigo-600 transition-colors"
                      >
                        <span>Cr</span>
                        {#if sortColumn === 'credits'}
                          {sortDirection === 'asc' ? '↑' : '↓'}
                        {:else}
                          <ArrowUpDown size={10} />
                        {/if}
                      </button>
                    </div>
                  </th>
                  <th class="p-4">
                    <button 
                      onclick={() => handleSort('term')}
                      class="flex items-center space-x-1 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest hover:text-indigo-600 transition-colors"
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
                        <span class="text-[10px] text-slate-400 dark:text-slate-500 truncate max-w-[200px]">{course.department}</span>
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
          <div class="flex items-center justify-between pt-8">
            <div class="text-sm text-slate-500 dark:text-slate-400">
              Showing <span class="font-bold text-slate-700 dark:text-slate-300">{offset + 1}</span> to 
              <span class="font-bold text-slate-700 dark:text-slate-300">{Math.min(offset + limit, totalHits)}</span> of 
              <span class="font-bold text-slate-700 dark:text-slate-300">{totalHits.toLocaleString()}</span>
            </div>
            <div class="flex space-x-2">
              <button 
                onclick={() => handlePageChange(offset - limit)}
                disabled={offset === 0}
                class="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors dark:bg-slate-900 dark:border-slate-800 dark:text-slate-300 dark:hover:bg-slate-800/60 shadow-sm"
              >
                Previous
              </button>
              <button 
                onclick={() => handlePageChange(offset + limit)}
                disabled={offset + limit >= totalHits}
                class="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors dark:bg-slate-900 dark:border-slate-800 dark:text-slate-300 dark:hover:bg-slate-800/60 shadow-sm"
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

