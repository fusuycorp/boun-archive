<script lang="ts">
  import { onMount } from "svelte";
  import { BookOpen, Search, ArrowRight, ChevronRight, Hash, ArrowUpDown } from "lucide-svelte";
  import { API_BASE } from "$lib/config";

  let departments = $state<any[]>([]);
  let selectedDept = $state<string | null>(null);
  let uniqueCourses = $state<any[]>([]);
  let loading = $state(false);
  let deptSearch = $state("");

  // Sorting
  let sortColumn = $state("latest_term");
  let sortDirection = $state<"asc" | "desc">("desc");

  async function fetchDepartments() {
    const res = await fetch(`${API_BASE}/api/v1/departments`);
    departments = await res.json();
    
    // Restore state if available
    const savedDept = sessionStorage.getItem("dept_selected");
    if (savedDept) {
      selectedDept = savedDept;
      const savedCourses = sessionStorage.getItem(`dept_courses_${savedDept}`);
      if (savedCourses) {
        uniqueCourses = JSON.parse(savedCourses);
      } else {
        fetchUniqueCourses(savedDept);
      }
    }
  }

  async function fetchUniqueCourses(deptCode: string) {
    loading = true;
    selectedDept = deptCode;
    sessionStorage.setItem("dept_selected", deptCode);
    try {
      const res = await fetch(`${API_BASE}/api/v1/departments/${deptCode}/unique-courses`);
      const data = await res.json();
      // Add latest_term field for easy sorting
      uniqueCourses = data.map((c: any) => ({
        ...c,
        latest_term: c.terms[0] || ""
      }));
      sessionStorage.setItem(`dept_courses_${deptCode}`, JSON.stringify(uniqueCourses));
    } finally {
      loading = false;
    }
  }

  function handleSort(column: string) {
    if (sortColumn === column) {
      sortDirection = sortDirection === "asc" ? "desc" : "asc";
    } else {
      sortColumn = column;
      sortDirection = column === "latest_term" ? "desc" : "asc";
    }
  }

  onMount(fetchDepartments);

  const filteredDepts = $derived(
    departments.filter(d => 
      d.kisaadi.toLowerCase().includes(deptSearch.toLowerCase()) || 
      d.bolum.toLowerCase().includes(deptSearch.toLowerCase())
    )
  );

  const sortedCourses = $derived(
    [...uniqueCourses].sort((a, b) => {
      const valA = a[sortColumn];
      const valB = b[sortColumn];
      if (valA < valB) return sortDirection === "asc" ? -1 : 1;
      if (valA > valB) return sortDirection === "asc" ? 1 : -1;
      return 0;
    })
  );
</script>

<div class="space-y-8">
  <div class="flex items-center justify-between">
    <div>
      <h2 class="text-3xl font-bold text-slate-800 dark:text-slate-100">Department Archive</h2>
      <p class="text-slate-500 dark:text-slate-400 mt-1">Explore all unique courses offered by departments across time.</p>
    </div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-4 gap-8">
    <!-- Sidebar: Dept List -->
    <aside class="space-y-4">
      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden dark:bg-slate-900 dark:border-slate-800 flex flex-col h-[calc(100vh-200px)] sticky top-24">
        <div class="p-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/50">
          <div class="relative">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input 
              type="text" 
              bind:value={deptSearch}
              placeholder="Search departments..."
              class="w-full pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 dark:bg-slate-950 dark:border-slate-800 dark:text-white transition-all"
            />
          </div>
        </div>
        
        <div class="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1">
          {#each filteredDepts as dept}
            <button 
              onclick={() => fetchUniqueCourses(dept.kisaadi)}
              class="w-full text-left p-3 rounded-xl transition-all group
              {selectedDept === dept.kisaadi 
                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-200 dark:shadow-none' 
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/60'}"
            >
              <div class="flex items-center justify-between">
                <div class="flex flex-col">
                  <span class="text-xs font-black uppercase tracking-widest opacity-60 {selectedDept === dept.kisaadi ? 'text-indigo-100' : ''}">{dept.kisaadi}</span>
                  <span class="text-sm font-bold truncate max-w-[180px]">{dept.bolum}</span>
                </div>
                <ChevronRight size={16} class="opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </button>
          {/each}
        </div>
      </div>
    </aside>

    <!-- Main Content: Course List -->
    <main class="lg:col-span-3 space-y-6">
      {#if loading}
        <div class="bg-white rounded-2xl border border-slate-200 p-24 flex flex-col items-center justify-center space-y-4 dark:bg-slate-900 dark:border-slate-800">
          <div class="animate-spin rounded-full h-12 w-12 border-4 border-slate-100 border-t-indigo-600 dark:border-slate-800 dark:border-t-indigo-500"></div>
          <p class="text-slate-500 dark:text-slate-400 font-medium">Loading historical course data...</p>
        </div>
      {:else if selectedDept}
        <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden dark:bg-slate-900 dark:border-slate-800">
          <div class="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-950/50">
            <div class="flex items-center space-x-3">
              <div class="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-200 dark:shadow-none">
                <BookOpen size={20} />
              </div>
              <div>
                <h3 class="text-xl font-bold text-slate-800 dark:text-slate-100">{selectedDept} Courses</h3>
                <p class="text-xs text-slate-500 dark:text-slate-400 font-medium">{uniqueCourses.length} unique classes found</p>
              </div>
            </div>
          </div>
          
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/50 dark:bg-slate-950/50 border-b border-slate-100 dark:border-slate-800">
                  <th class="p-4">
                    <button 
                      onclick={() => handleSort('course_code')}
                      class="flex items-center space-x-1 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest hover:text-indigo-600 transition-colors"
                    >
                      <span>Code</span>
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
                      <span>Historical Title</span>
                      {#if sortColumn === 'title'}
                        {sortDirection === 'asc' ? '↑' : '↓'}
                      {:else}
                        <ArrowUpDown size={10} />
                      {/if}
                    </button>
                  </th>
                  <th class="p-4">
                    <button 
                      onclick={() => handleSort('latest_term')}
                      class="flex items-center space-x-1 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest hover:text-indigo-600 transition-colors"
                    >
                      <span>Latest Term</span>
                      {#if sortColumn === 'latest_term'}
                        {sortDirection === 'asc' ? '↑' : '↓'}
                      {:else}
                        <ArrowUpDown size={10} />
                      {/if}
                    </button>
                  </th>
                  <th class="p-4 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">Active Semesters</th>
                  <th class="p-4"></th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-50 dark:divide-slate-800/50">
                {#each sortedCourses as course}
                  <tr class="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors group">
                    <td class="p-4 whitespace-nowrap">
                      <span class="text-sm font-bold text-indigo-600 dark:text-indigo-400">{course.course_code}</span>
                    </td>
                    <td class="p-4">
                      <span class="text-sm font-bold text-slate-700 dark:text-slate-200">{course.title}</span>
                    </td>
                    <td class="p-4 whitespace-nowrap">
                      <span class="text-xs font-bold text-slate-500 dark:text-slate-400">{course.latest_term}</span>
                    </td>
                    <td class="p-4">
                      <div class="flex flex-wrap gap-1">
                        {#each course.terms.slice(0, 3) as term}
                          <span class="px-2 py-0.5 bg-slate-100 text-slate-600 text-[9px] font-bold rounded-md dark:bg-slate-800 dark:text-slate-400 border border-slate-200 dark:border-slate-700">{term}</span>
                        {/each}
                        {#if course.terms.length > 3}
                          <span class="px-2 py-0.5 bg-indigo-50 text-indigo-600 text-[9px] font-black rounded-md dark:bg-indigo-950/40 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-900/50">+{course.terms.length - 3} MORE</span>
                        {/if}
                      </div>
                    </td>
                    <td class="p-4 text-right">
                      <a 
                        href="/course/{course.course_code}"
                        class="inline-flex items-center space-x-2 text-xs font-bold text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
                      >
                        <span>History</span>
                        <ArrowRight size={14} />
                      </a>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {:else}
        <div class="bg-white rounded-3xl border-2 border-dashed border-slate-200 p-24 flex flex-col items-center justify-center text-center dark:bg-slate-900 dark:border-slate-800">
          <div class="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center text-slate-300 mb-6 dark:bg-slate-950 dark:text-slate-800">
            <BookOpen size={40} />
          </div>
          <h3 class="text-2xl font-bold text-slate-800 dark:text-slate-200">Select a department</h3>
          <p class="text-slate-500 dark:text-slate-400 mt-2 max-w-sm">Choose a department from the sidebar to view its historical course catalog and offered semesters.</p>
        </div>
      {/if}
    </main>
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
</style>
