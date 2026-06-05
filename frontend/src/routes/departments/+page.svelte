<script lang="ts">
  import { onMount } from "svelte";
  import { BookOpen, Search, ArrowRight, ChevronRight, Hash, ArrowUpDown, User, Download } from "lucide-svelte";
  import { API_BASE } from "$lib/config";
  import { exportToCSV } from "$lib/utils";

  let departments = $state<any[]>([]);
  let selectedDept = $state<string | null>(null);
  let uniqueCourses = $state<any[]>([]);
  let deptInstructors = $state<any[]>([]);
  let loading = $state(false);
  let deptSearch = $state("");
  let viewMode = $state<"courses" | "instructors">("courses");

  // Sorting - Courses
  let courseSortColumn = $state("latest_term");
  let courseSortDirection = $state<"asc" | "desc">("desc");

  // Sorting - Instructors
  let instructorSortColumn = $state("last_term");
  let instructorSortDirection = $state<"asc" | "desc">("desc");

  async function fetchDepartments() {
    const res = await fetch(`${API_BASE}/api/v1/departments`);
    departments = await res.json();
    
    // Restore state if available
    const savedDept = sessionStorage.getItem("dept_selected");
    const savedView = sessionStorage.getItem("dept_view_mode") as any;
    
    if (savedView) viewMode = savedView;

    if (savedDept) {
      selectedDept = savedDept;
      const savedCourses = sessionStorage.getItem(`dept_courses_${savedDept}`);
      if (savedCourses) {
        uniqueCourses = JSON.parse(savedCourses);
      } else {
        fetchUniqueCourses(savedDept);
      }

      const savedInstructors = sessionStorage.getItem(`dept_instructors_${savedDept}`);
      if (savedInstructors) {
        deptInstructors = JSON.parse(savedInstructors);
      } else {
        fetchDeptInstructors(savedDept);
      }
    }
  }

  async function fetchUniqueCourses(deptCode: string) {
    try {
      const res = await fetch(`${API_BASE}/api/v1/departments/${deptCode}/unique-courses`);
      const data = await res.json();
      uniqueCourses = data.map((c: any) => ({
        ...c,
        latest_term: c.terms[0] || ""
      }));
      sessionStorage.setItem(`dept_courses_${deptCode}`, JSON.stringify(uniqueCourses));
    } catch (e) {
      console.error(e);
    }
  }

  async function fetchDeptInstructors(deptCode: string) {
    try {
      const res = await fetch(`${API_BASE}/api/v1/departments/${deptCode}/instructors`);
      const data = await res.json();
      deptInstructors = data;
      sessionStorage.setItem(`dept_instructors_${deptCode}`, JSON.stringify(deptInstructors));
    } catch (e) {
      console.error(e);
    }
  }

  async function handleDeptSelect(deptCode: string) {
    loading = true;
    selectedDept = deptCode;
    sessionStorage.setItem("dept_selected", deptCode);
    
    await Promise.all([
      fetchUniqueCourses(deptCode),
      fetchDeptInstructors(deptCode)
    ]);
    
    loading = false;
  }

  function handleCourseSort(column: string) {
    if (courseSortColumn === column) {
      courseSortDirection = courseSortDirection === "asc" ? "desc" : "asc";
    } else {
      courseSortColumn = column;
      courseSortDirection = column === "latest_term" ? "desc" : "asc";
    }
  }

  function handleInstructorSort(column: string) {
    if (instructorSortColumn === column) {
      instructorSortDirection = instructorSortDirection === "asc" ? "desc" : "asc";
    } else {
      instructorSortColumn = column;
      instructorSortDirection = column === "last_term" ? "desc" : "asc";
    }
  }

  function setViewMode(mode: "courses" | "instructors") {
    viewMode = mode;
    sessionStorage.setItem("dept_view_mode", mode);
  }

  function handleExport() {
    if (viewMode === 'courses') {
      if (uniqueCourses.length === 0) return;
      const exportData = sortedCourses.map(c => ({
        course_code: c.course_code,
        title: c.title,
        latest_term: c.latest_term,
        all_terms: c.terms.join('; ')
      }));
      exportToCSV(exportData, `boun_dept_${selectedDept}_courses_${new Date().toISOString().split('T')[0]}`);
    } else {
      if (deptInstructors.length === 0) return;
      const exportData = sortedInstructors.map(i => ({
        full_name: i.full_name,
        last_term: i.last_term,
        course_count: i.course_count,
        total_semesters: i.total_semesters
      }));
      exportToCSV(exportData, `boun_dept_${selectedDept}_instructors_${new Date().toISOString().split('T')[0]}`);
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
      const valA = a[courseSortColumn];
      const valB = b[courseSortColumn];
      if (valA < valB) return courseSortDirection === "asc" ? -1 : 1;
      if (valA > valB) return courseSortDirection === "asc" ? 1 : -1;
      return 0;
    })
  );

  const sortedInstructors = $derived(
    [...deptInstructors].sort((a, b) => {
      const valA = a[instructorSortColumn];
      const valB = b[instructorSortColumn];
      if (valA < valB) return instructorSortDirection === "asc" ? -1 : 1;
      if (valA > valB) return instructorSortDirection === "asc" ? 1 : -1;
      return 0;
    })
  );
</script>

<div class="space-y-8">
  <div class="flex items-center justify-between">
    <div>
      <h2 class="text-3xl font-bold text-slate-800 dark:text-slate-100">Department Archive</h2>
      <p class="text-slate-500 dark:text-slate-400 mt-1">Explore courses and instructors across decades of academic history.</p>
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
              onclick={() => handleDeptSelect(dept.kisaadi)}
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

    <!-- Main Content -->
    <main class="lg:col-span-3 space-y-6">
      {#if loading}
        <div class="bg-white rounded-2xl border border-slate-200 p-24 flex flex-col items-center justify-center space-y-4 dark:bg-slate-900 dark:border-slate-800">
          <div class="animate-spin rounded-full h-12 w-12 border-4 border-slate-100 border-t-indigo-600 dark:border-slate-800 dark:border-t-indigo-500"></div>
          <p class="text-slate-500 dark:text-slate-400 font-medium">Synchronizing records...</p>
        </div>
      {:else if selectedDept}
        <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden dark:bg-slate-900 dark:border-slate-800">
          <div class="p-6 border-b border-slate-100 dark:border-slate-800 flex flex-col lg:flex-row lg:items-center justify-between bg-slate-50/50 dark:bg-slate-950/50 gap-4">
            <div class="flex items-center space-x-3">
              <div class="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-200 dark:shadow-none">
                {#if viewMode === 'courses'}
                   <BookOpen size={20} />
                {:else}
                   <User size={20} />
                {/if}
              </div>
              <div>
                <h3 class="text-xl font-bold text-slate-800 dark:text-slate-100">{selectedDept} {viewMode === 'courses' ? 'Courses' : 'Instructors'}</h3>
                <p class="text-xs text-slate-500 dark:text-slate-400 font-medium">
                   {viewMode === 'courses' ? uniqueCourses.length : deptInstructors.length} records found
                </p>
              </div>
            </div>

            <div class="flex items-center space-x-3">
              <!-- Tab Switcher -->
              <div class="flex bg-slate-200/50 dark:bg-slate-800/50 p-1 rounded-xl">
                 <button 
                  onclick={() => setViewMode('courses')}
                  class="px-4 py-1.5 text-xs font-bold rounded-lg transition-all {viewMode === 'courses' ? 'bg-white text-indigo-600 shadow-sm dark:bg-slate-700 dark:text-white' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400'}"
                 >Courses</button>
                 <button 
                  onclick={() => setViewMode('instructors')}
                  class="px-4 py-1.5 text-xs font-bold rounded-lg transition-all {viewMode === 'instructors' ? 'bg-white text-indigo-600 shadow-sm dark:bg-slate-700 dark:text-white' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400'}"
                 >Instructors</button>
              </div>

              <button 
                  onclick={handleExport}
                  class="flex items-center space-x-2 bg-white border border-slate-200 text-slate-600 px-4 py-1.5 rounded-xl text-xs font-bold hover:bg-slate-50 transition-colors shadow-sm dark:bg-slate-800 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700"
              >
                <Download size={14} />
                <span class="hidden sm:inline">Export CSV</span>
              </button>
            </div>
          </div>
          
          <div class="overflow-x-auto">
            {#if viewMode === 'courses'}
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="bg-slate-50/50 dark:bg-slate-950/50 border-b border-slate-100 dark:border-slate-800">
                    <th class="p-4">
                      <button onclick={() => handleCourseSort('course_code')} class="flex items-center space-x-1 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest hover:text-indigo-600 transition-colors">
                        <span>Code</span>
                        {#if courseSortColumn === 'course_code'}{courseSortDirection === 'asc' ? '↑' : '↓'}{:else}<ArrowUpDown size={10} />{/if}
                      </button>
                    </th>
                    <th class="p-4">
                      <button onclick={() => handleCourseSort('title')} class="flex items-center space-x-1 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest hover:text-indigo-600 transition-colors">
                        <span>Historical Title</span>
                        {#if courseSortColumn === 'title'}{courseSortDirection === 'asc' ? '↑' : '↓'}{:else}<ArrowUpDown size={10} />{/if}
                      </button>
                    </th>
                    <th class="p-4">
                      <button onclick={() => handleCourseSort('latest_term')} class="flex items-center space-x-1 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest hover:text-indigo-600 transition-colors">
                        <span>Latest Term</span>
                        {#if courseSortColumn === 'latest_term'}{courseSortDirection === 'asc' ? '↑' : '↓'}{:else}<ArrowUpDown size={10} />{/if}
                      </button>
                    </th>
                    <th class="p-4 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">Active Semesters</th>
                    <th class="p-4"></th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-50 dark:divide-slate-800/50">
                  {#each sortedCourses as course}
                    <tr class="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors group">
                      <td class="p-4 whitespace-nowrap"><span class="text-sm font-bold text-indigo-600 dark:text-indigo-400">{course.course_code}</span></td>
                      <td class="p-4"><span class="text-sm font-bold text-slate-700 dark:text-slate-200">{course.title}</span></td>
                      <td class="p-4 whitespace-nowrap"><span class="text-xs font-bold text-slate-500 dark:text-slate-400">{course.latest_term}</span></td>
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
                        <a href="/course/{course.course_code}" class="inline-flex items-center space-x-2 text-xs font-bold text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
                          <span>History</span> <ArrowRight size={14} />
                        </a>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            {:else}
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="bg-slate-50/50 dark:bg-slate-950/50 border-b border-slate-100 dark:border-slate-800">
                    <th class="p-4">
                      <button onclick={() => handleInstructorSort('full_name')} class="flex items-center space-x-1 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest hover:text-indigo-600 transition-colors">
                        <span>Instructor Name</span>
                        {#if instructorSortColumn === 'full_name'}{instructorSortDirection === 'asc' ? '↑' : '↓'}{:else}<ArrowUpDown size={10} />{/if}
                      </button>
                    </th>
                    <th class="p-4">
                      <button onclick={() => handleInstructorSort('last_term')} class="flex items-center space-x-1 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest hover:text-indigo-600 transition-colors">
                        <span>Last Term in Dept</span>
                        {#if instructorSortColumn === 'last_term'}{instructorSortDirection === 'asc' ? '↑' : '↓'}{:else}<ArrowUpDown size={10} />{/if}
                      </button>
                    </th>
                    <th class="p-4 text-center">
                      <button onclick={() => handleInstructorSort('course_count')} class="flex items-center justify-center space-x-1 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest hover:text-indigo-600 transition-colors">
                        <span>Classes</span>
                        {#if instructorSortColumn === 'course_count'}{instructorSortDirection === 'asc' ? '↑' : '↓'}{:else}<ArrowUpDown size={10} />{/if}
                      </button>
                    </th>
                    <th class="p-4 text-center">
                      <button onclick={() => handleInstructorSort('total_semesters')} class="flex items-center justify-center space-x-1 text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest hover:text-indigo-600 transition-colors">
                        <span>Semesters</span>
                        {#if instructorSortColumn === 'total_semesters'}{instructorSortDirection === 'asc' ? '↑' : '↓'}{:else}<ArrowUpDown size={10} />{/if}
                      </button>
                    </th>
                    <th class="p-4"></th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-50 dark:divide-slate-800/50">
                  {#each sortedInstructors as instructor}
                    <tr class="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors group">
                      <td class="p-4 whitespace-nowrap">
                        <a 
                          href="/instructor/{instructor.id}"
                          class="flex items-center space-x-3 group/item"
                        >
                          <div class="w-7 h-7 bg-slate-100 rounded-full flex items-center justify-center text-slate-400 dark:bg-slate-800 dark:text-slate-600 group-hover/item:bg-indigo-100 group-hover/item:text-indigo-600 transition-colors">
                            <User size={14} />
                          </div>
                          <span class="text-sm font-bold text-slate-700 dark:text-slate-200 group-hover/item:text-indigo-600 transition-colors">{instructor.full_name}</span>
                        </a>
                      </td>
                      <td class="p-4 whitespace-nowrap"><span class="text-xs font-bold text-slate-500 dark:text-slate-400">{instructor.last_term}</span></td>
                      <td class="p-4 text-center"><span class="text-xs font-black text-slate-600 dark:text-slate-300">{instructor.course_count}</span></td>
                      <td class="p-4 text-center"><span class="text-xs font-black text-slate-600 dark:text-slate-300">{instructor.total_semesters}</span></td>
                      <td class="p-4 text-right">
                         <a href="/instructor/{instructor.id}" class="text-slate-300 hover:text-indigo-600 dark:text-slate-700 dark:hover:text-indigo-400 transition-colors"><ChevronRight size={14} /></a>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            {/if}
          </div>
        </div>
      {:else}
        <div class="bg-white rounded-3xl border-2 border-dashed border-slate-200 p-24 flex flex-col items-center justify-center text-center dark:bg-slate-900 dark:border-slate-800">
          <div class="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center text-slate-300 mb-6 dark:bg-slate-950 dark:text-slate-800">
            <BookOpen size={40} />
          </div>
          <h3 class="text-2xl font-bold text-slate-800 dark:text-slate-200">Select a department</h3>
          <p class="text-slate-500 dark:text-slate-400 mt-2 max-w-sm">Choose a department from the sidebar to view its historical course catalog and instructor rosters.</p>
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
