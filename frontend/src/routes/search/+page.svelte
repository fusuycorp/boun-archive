<script lang="ts">
  import { onMount } from "svelte";
  import { Search, Filter, BookOpen, User, Calendar, MapPin } from "lucide-svelte";

  let query = $state("");
  let results = $state<any[]>([]);
  let facets = $state<any>({});
  let loading = $state(false);
  let totalHits = $state(0);

  // Filters
  let selectedTerm = $state("");
  let selectedDept = $state("");

  async function performSearch() {
    loading = true;
    try {
      const params = new URLSearchParams({
        q: query,
        limit: "20"
      });
      if (selectedTerm) params.append("term", selectedTerm);
      if (selectedDept) params.append("dept", selectedDept);

      const response = await fetch(`http://localhost:8000/api/v1/search?${params.toString()}`);
      const data = await response.json();
      results = data.hits;
      facets = data.facetDistribution;
      totalHits = data.totalHits;
    } catch (e) {
      console.error("Search failed", e);
    } finally {
      loading = false;
    }
  }

  // Debounced search
  let timeout: any;
  function handleInput() {
    clearTimeout(timeout);
    timeout = setTimeout(performSearch, 300);
  }

  onMount(() => {
    performSearch();
  });
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <h2 class="text-3xl font-bold text-slate-800">Course Search</h2>
    <div class="text-sm text-slate-500 font-medium">
      {totalHits.toLocaleString()} results found
    </div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-4 gap-8">
    <!-- Sidebar Filters -->
    <aside class="space-y-6">
      <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div class="flex items-center space-x-2 text-slate-700 font-semibold mb-2">
          <Filter size={18} />
          <span>Filters</span>
        </div>

        <div>
          <label class="text-xs font-bold text-slate-400 uppercase tracking-wider">Term</label>
          <select 
            bind:value={selectedTerm} 
            onchange={performSearch}
            class="mt-1 w-full p-2 bg-slate-50 border border-slate-200 rounded-md text-sm outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Terms</option>
            {#if facets.term}
              {#each Object.keys(facets.term).sort().reverse() as term}
                <option value={term}>{term}</option>
              {each}
            {/if}
          </select>
        </div>

        <div>
          <label class="text-xs font-bold text-slate-400 uppercase tracking-wider">Department</label>
          <select 
            bind:value={selectedDept} 
            onchange={performSearch}
            class="mt-1 w-full p-2 bg-slate-50 border border-slate-200 rounded-md text-sm outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Departments</option>
            {#if facets.dept_code}
              {#each Object.keys(facets.dept_code).sort() as dept}
                <option value={dept}>{dept}</option>
              {each}
            {/if}
          </select>
        </div>
      </div>
    </aside>

    <!-- Search Results -->
    <div class="lg:col-span-3 space-y-4">
      <div class="relative">
        <Search class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
        <input
          type="text"
          bind:value={query}
          oninput={handleInput}
          placeholder="Search by code, title, or instructor..."
          class="w-full pl-12 pr-4 py-4 bg-white border border-slate-200 rounded-xl shadow-sm outline-none focus:ring-2 focus:ring-indigo-500 text-lg"
        />
      </div>

      {#if loading}
        <div class="flex justify-center py-12">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>
      {:else}
        <div class="grid grid-cols-1 gap-4">
          {#each results as course}
            <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm hover:border-indigo-300 transition-colors group">
              <div class="flex justify-between items-start">
                <div>
                  <div class="flex items-center space-x-2">
                    <span class="px-2 py-1 bg-indigo-50 text-indigo-700 text-xs font-bold rounded uppercase">{course.course_code}</span>
                    <span class="text-xs text-slate-400 font-medium">Section {course.section}</span>
                  </div>
                  <h3 class="text-xl font-bold text-slate-800 mt-2 group-hover:text-indigo-600 transition-colors">{course.title}</h3>
                </div>
                <div class="text-right">
                  <div class="text-sm font-bold text-slate-700">{course.credits} Credits</div>
                  <div class="text-xs text-slate-400">{course.ects} ECTS</div>
                </div>
              </div>

              <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-slate-50">
                <div class="flex items-center space-x-2 text-slate-600">
                  <User size={16} class="text-slate-400" />
                  <span class="text-sm truncate">{course.instructor}</span>
                </div>
                <div class="flex items-center space-x-2 text-slate-600">
                  <BookOpen size={16} class="text-slate-400" />
                  <span class="text-sm truncate">{course.department}</span>
                </div>
                <div class="flex items-center space-x-2 text-slate-600">
                  <Calendar size={16} class="text-slate-400" />
                  <span class="text-sm">{course.term}</span>
                </div>
                <div class="flex items-center space-x-2 text-slate-600">
                  <MapPin size={16} class="text-slate-400" />
                  <span class="text-sm">{course.delivery_method || 'Standard'}</span>
                </div>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  </div>
</div>
